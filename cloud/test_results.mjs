import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import worker from "./worker.mjs";

const base = "https://example.workers.dev";
function environment() {
  const sqlite = new DatabaseSync(":memory:");
  sqlite.exec(readFileSync(new URL("./migrations/0001_initial.sql", import.meta.url), "utf8"));
  const DB = {
    prepare(sql) {
      return { bind(...args) {
        return { sql, args,
          async run() { return sqlite.prepare(sql).run(...args); },
          async first() { return sqlite.prepare(sql).get(...args) || null; },
          async all() { return { results: sqlite.prepare(sql).all(...args) }; },
        };
      } };
    },
    async batch(statements) {
      sqlite.exec("BEGIN");
      try { const values = statements.map(({ sql, args }) => sqlite.prepare(sql).run(...args)); sqlite.exec("COMMIT"); return values; }
      catch (error) { sqlite.exec("ROLLBACK"); throw error; }
    },
  };
  return { sqlite, env: { DB, ACCESS_SECRET: "a".repeat(40), SESSION_KEY: "b".repeat(40), WORKER_SECRET: "c".repeat(40) } };
}
const request = (path, method, body, headers = {}) => new Request(`${base}${path}`, { method, headers: { Origin: base, ...(body ? { "Content-Type": "application/json" } : {}), ...headers }, ...(body ? { body: JSON.stringify(body) } : {}) });

test("chunked results survive duplicate delivery and have no global match cap", async () => {
  const { sqlite, env } = environment();
  try {
    const login = await worker.fetch(request("/api/v1/session", "POST", { access_secret: env.ACCESS_SECRET }), env);
    assert.equal(login.status, 200);
    const { csrf_token } = await login.json();
    const cookie = login.headers.get("Set-Cookie").split(";")[0];
    const criteria = { schema_version: 1, location: "91304", radius_miles: 2, party_size: 7, max_total_price: 85, cuisines: [], restaurant_type: "any", open_tonight: false };
    const created = await worker.fetch(request("/api/v1/searches", "POST", { module: "family-deals", criteria }, { Cookie: cookie, "X-CSRF-Token": csrf_token }), env);
    assert.equal(created.status, 202);
    const searchId = (await created.json()).id;
    const headers = { Authorization: `Bearer ${env.WORKER_SECRET}` };
    const targetJobId = sqlite.prepare("SELECT id FROM jobs WHERE search_id=?").get(searchId).id;
    const claim = await worker.fetch(request("/api/v1/internal/jobs/claim", "POST", { limit: 1, module: "family-deals", job_id: targetJobId }, headers), env);
    assert.equal(claim.status, 200);
    const job = (await claim.json()).jobs[0];
    assert.deepEqual(job.criteria, criteria);
    const progressCoverage = { state: "partial", radius_discovered: 12, discovered: 12, checked: 3, unavailable: 1, unresolved: 2 };
    const progressResponse = await worker.fetch(request(`/api/v1/internal/jobs/${job.id}/progress`, "POST", {
      claim_id: job.claim_id, coverage: progressCoverage, summary: "3 checked so far",
    }, headers), env);
    assert.equal(progressResponse.status, 200, await progressResponse.text());
    const activeProgress = await worker.fetch(request(`/api/v1/searches/${searchId}`, "GET", null, { Cookie: cookie }), env);
    assert.deepEqual((await activeProgress.json()).coverage, progressCoverage);
    const invalidProgress = await worker.fetch(request(`/api/v1/internal/jobs/${job.id}/progress`, "POST", {
      claim_id: job.claim_id, coverage: { ...progressCoverage, checked: 20 },
    }, headers), env);
    assert.equal(invalidProgress.status, 400);
    const invalidRadius = await worker.fetch(request(`/api/v1/internal/jobs/${job.id}/progress`, "POST", {
      claim_id: job.claim_id, coverage: { ...progressCoverage, radius_discovered: 2 },
    }, headers), env);
    assert.equal(invalidRadius.status, 400);
    const items = Array.from({ length: 12 }, (_, i) => ({
      id: `00000000-0000-4000-8000-${String(i).padStart(12, "0")}`,
      title: `Meal ${i}`, outcome: "MATCH", verification: "VERIFIED", summary: "Official menu",
      details: { deal_name: `Meal ${i}`, restaurant: "Example Restaurant", price_cents: 5000, serves_max: 7, meal_verified: true, price_verified: true, capacity_verified: true, location_verified: true },
      evidence: [{ source: "Restaurant menu", summary: "Meal and total price for seven", url: "https://example.com/menu" }],
    }));
    for (let i = 0; i < items.length; i += 5) {
      const chunk = { claim_id: job.claim_id, items: items.slice(i, i + 5) };
      const path = `/api/v1/internal/jobs/${job.id}/results`;
      const first = await worker.fetch(request(path, "POST", chunk, headers), env);
      assert.equal(first.status, 200, await first.text());
      const repeat = await worker.fetch(request(path, "POST", chunk, headers), env);
      assert.equal(repeat.status, 200);
    }
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM results").get().n, 12);
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM result_evidence").get().n, 12);
    const progressive = await worker.fetch(request(`/api/v1/results?search_id=${searchId}`, "GET", null, { Cookie: cookie }), env);
    assert.equal((await progressive.json()).results.length, 12);
    assert.equal((await worker.fetch(request(`/api/v1/results/${items[0].id}`, "GET", null, { Cookie: cookie }), env)).status, 200);
    const runningSearch = await worker.fetch(request(`/api/v1/searches/${searchId}`, "GET", null, { Cookie: cookie }), env);
    assert.equal((await runningSearch.json()).status, "RUNNING");
    const conflict = await worker.fetch(request(`/api/v1/internal/jobs/${job.id}/results`, "POST", { claim_id: job.claim_id, items: [{ ...items[0], title: "Changed title" }] }, headers), env);
    assert.equal(conflict.status, 409);
    assert.equal(sqlite.prepare("SELECT title FROM results WHERE id=?").get(items[0].id).title, "Meal 0");
    const aboveBudget = await worker.fetch(request(`/api/v1/internal/jobs/${job.id}/results`, "POST", { claim_id: job.claim_id, items: [{ ...items[0], id: crypto.randomUUID(), details: { ...items[0].details, price_cents: 8501 } }] }, headers), env);
    assert.equal(aboveBudget.status, 400);
    const completePath = `/api/v1/internal/jobs/${job.id}/complete`;
    const coverage = { state: "complete", discovered: 12, checked: 12, unavailable: 0, unresolved: 0 };
    const completion = { claim_id: job.claim_id, outcome: "MATCH", summary: "12 verified meals", coverage };
    const finalized = await worker.fetch(request(completePath, "POST", completion, headers), env);
    assert.equal(finalized.status, 200, await finalized.text());
    assert.equal((await worker.fetch(request(completePath, "POST", completion, headers), env)).status, 200);
    assert.equal((await worker.fetch(request(completePath, "POST", { ...completion, summary: "Different" }, headers), env)).status, 409);
    const search = await worker.fetch(request(`/api/v1/searches/${searchId}`, "GET", null, { Cookie: cookie }), env);
    const completedSearch = await search.json();
    assert.equal(completedSearch.last_outcome, "MATCH");
    assert.equal(completedSearch.coverage.radius_discovered, 12);
    assert.equal(sqlite.prepare("SELECT status FROM jobs WHERE id=?").get(job.id).status, "COMPLETED");
    const pageOne = await worker.fetch(request(`/api/v1/results?search_id=${searchId}&limit=5`, "GET", null, { Cookie: cookie }), env);
    assert.equal(pageOne.status, 200);
    const firstPage = await pageOne.json();
    assert.equal(firstPage.results.length, 5);
    assert.ok(firstPage.next_cursor);
    const cursor = new URLSearchParams({ search_id: searchId, limit: "5", ...firstPage.next_cursor });
    const pageTwo = await worker.fetch(request(`/api/v1/results?${cursor}`, "GET", null, { Cookie: cookie }), env);
    assert.equal((await pageTwo.json()).results.length, 5);
    const detail = await worker.fetch(request(`/api/v1/results/${firstPage.results[0].id}`, "GET", null, { Cookie: cookie }), env);
    assert.equal((await detail.json()).evidence.length, 1);
  } finally { sqlite.close(); }
});

test("partial provider coverage cannot finalize as no-match", async () => {
  const { sqlite, env } = environment();
  try {
    const login = await worker.fetch(request("/api/v1/session", "POST", { access_secret: env.ACCESS_SECRET }), env);
    const { csrf_token } = await login.json();
    const cookie = login.headers.get("Set-Cookie").split(";")[0];
    const criteria = { schema_version: 1, location: "91304", radius_miles: 2, party_size: 7, max_total_price: 85, cuisines: [], restaurant_type: "any", open_tonight: false };
    await worker.fetch(request("/api/v1/searches", "POST", { module: "family-deals", criteria }, { Cookie: cookie, "X-CSRF-Token": csrf_token }), env);
    const headers = { Authorization: `Bearer ${env.WORKER_SECRET}` };
    const targetJobId = sqlite.prepare("SELECT id FROM jobs WHERE search_id=?").get(sqlite.prepare("SELECT id FROM searches WHERE user_id='private-beta'").get().id).id;
    const job = (await (await worker.fetch(request("/api/v1/internal/jobs/claim", "POST", { limit: 1, module: "family-deals", job_id: targetJobId }, headers), env)).json()).jobs[0];
    const completion = { claim_id: job.claim_id, outcome: "NO_MATCH", summary: "None found", coverage: { state: "partial", discovered: 12, checked: 9, unavailable: 3, unresolved: 0 } };
    assert.equal((await worker.fetch(request(`/api/v1/internal/jobs/${job.id}/complete`, "POST", completion, headers), env)).status, 400);
    assert.equal(sqlite.prepare("SELECT status FROM jobs WHERE id=?").get(job.id).status, "CLAIMED");
    const completeCoverage = { state: "complete", discovered: 12, checked: 12, unavailable: 0, unresolved: 0 };
    assert.equal((await worker.fetch(request(`/api/v1/internal/jobs/${job.id}/complete`, "POST", { ...completion, coverage: completeCoverage }, headers), env)).status, 200);
    assert.equal(sqlite.prepare("SELECT status FROM jobs WHERE id=?").get(job.id).status, "COMPLETED");
  } finally { sqlite.close(); }
});
