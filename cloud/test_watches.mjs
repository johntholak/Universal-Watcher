import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import worker from "./worker.mjs";
import { restoreFreeCapacity } from "./dispatch.mjs";

const base = "https://example.workers.dev";
const criteria = { schema_version: 1, location: "91304", radius_miles: 7,
  party_size: 7, max_total_price: 85.01, cuisines: ["pizza_italian", "bbq"],
  restaurant_type: "independent_local", open_tonight: true };
const request = (path, method = "GET", body, headers = {}) => new Request(base + path, {
  method, headers: { Origin: base, ...(body ? { "Content-Type": "application/json" } : {}), ...headers },
  ...(body ? { body: JSON.stringify(body) } : {}),
});

function environment() {
  const sqlite = new DatabaseSync(":memory:");
  for (const migration of ["0001_initial.sql", "0002_dispatch_gate.sql", "0003_watch_jobs.sql", "0004_watch_criteria_versions.sql"])
    sqlite.exec(readFileSync(new URL(`./migrations/${migration}`, import.meta.url), "utf8"));
  const DB = {
    prepare(sql) { return { bind(...args) { return { sql, args,
      async run() { return sqlite.prepare(sql).run(...args); },
      async first() { return sqlite.prepare(sql).get(...args) || null; },
      async all() { return { results: sqlite.prepare(sql).all(...args) }; },
    }; } }; },
    async batch(statements) {
      sqlite.exec("BEGIN");
      try { const output = statements.map(({ sql, args }) => sqlite.prepare(sql).run(...args)); sqlite.exec("COMMIT"); return output; }
      catch (error) { sqlite.exec("ROLLBACK"); throw error; }
    },
  };
  return { sqlite, env: { DB, ACCESS_SECRET: "a".repeat(40), SESSION_KEY: "b".repeat(40), WORKER_SECRET: "c".repeat(40) } };
}
async function session(env) {
  const response = await worker.fetch(request("/api/v1/session", "POST", { access_secret: env.ACCESS_SECRET }), env);
  assert.equal(response.status, 200);
  return { Cookie: response.headers.get("Set-Cookie").split(";")[0],
    "X-CSRF-Token": (await response.json()).csrf_token };
}
async function createSearchAndWatch(env, headers) {
  const search = await worker.fetch(request("/api/v1/searches", "POST", { module: "family-deals", criteria }, headers), env);
  assert.equal(search.status, 202);
  const searchId = (await search.json()).id;
  const tooEarly = await worker.fetch(request("/api/v1/watches", "POST", { search_id: searchId }, headers), env);
  assert.equal(tooEarly.status, 409);
  await env.DB.prepare("UPDATE searches SET status='COMPLETED' WHERE id=?").bind(searchId).run();
  const response = await worker.fetch(request("/api/v1/watches", "POST", { search_id: searchId }, headers), env);
  const body = await response.json();
  assert.equal(response.status, 201, JSON.stringify(body));
  return { searchId, watchId: body.id };
}

test("Watch copies exact Search criteria, is user-scoped, and manual checks deduplicate", async (t) => {
  const { sqlite, env } = environment(); t.after(() => sqlite.close());
  const headers = await session(env);
  const { searchId, watchId } = await createSearchAndWatch(env, headers);
  sqlite.prepare("UPDATE searches SET criteria_json='{}' WHERE id=?").run(searchId);
  const detail = await worker.fetch(request(`/api/v1/watches/${watchId}`, "GET", null, headers), env);
  assert.deepEqual((await detail.json()).criteria, criteria);
  const list = await worker.fetch(request("/api/v1/watches", "GET", null, headers), env);
  assert.equal((await list.json()).watches.length, 1);
  const first = await worker.fetch(request(`/api/v1/watches/${watchId}/check`, "POST", {}, headers), env);
  assert.equal(first.status, 202, await first.text());
  assert.equal((await worker.fetch(request(`/api/v1/watches/${watchId}/check`, "POST", {}, headers), env)).status, 409);
  const job = sqlite.prepare("SELECT criteria_json FROM watches WHERE id=?").get(watchId);
  assert.deepEqual(JSON.parse(job.criteria_json), criteria);
  assert.equal(sqlite.prepare("SELECT count(*) AS n FROM jobs WHERE watch_id=?").get(watchId).n, 1);
  sqlite.prepare("INSERT INTO users(id,created_at) VALUES ('other',?)").run(new Date().toISOString());
  sqlite.prepare("UPDATE watches SET user_id='other' WHERE id=?").run(watchId);
  assert.equal((await worker.fetch(request(`/api/v1/watches/${watchId}`, "GET", null, headers), env)).status, 404);
});

test("Cron queues due Watch once; completion records only meaningful history", async (t) => {
  const { sqlite, env } = environment(); t.after(() => sqlite.close());
  const headers = await session(env);
  const { watchId } = await createSearchAndWatch(env, headers);
  sqlite.prepare("UPDATE jobs SET status='COMPLETED' WHERE search_id IS NOT NULL").run();
  sqlite.prepare("UPDATE watches SET next_check_at=? WHERE id=?").run("2020-01-01T00:00:00.000Z", watchId);
  await worker.scheduled({ cron: "*/15 * * * *" }, env);
  await worker.scheduled({ cron: "*/15 * * * *" }, env);
  assert.equal(sqlite.prepare("SELECT count(*) AS n FROM jobs WHERE watch_id=?").get(watchId).n, 1);
  const internal = { Authorization: `Bearer ${env.WORKER_SECRET}` };
  const claim = await worker.fetch(request("/api/v1/internal/jobs/claim", "POST", { module: "family-deals", limit: 1 }, internal), env);
  const job = (await claim.json()).jobs[0];
  assert.equal(job.watch_id, watchId);
  assert.deepEqual(job.criteria, criteria);
  const completion = { claim_id: job.claim_id, outcome: "NO_MATCH", summary: "No qualifying meal among checked restaurants",
    coverage: { state: "complete", discovered: 2, checked: 2, unavailable: 0, unresolved: 0 } };
  const endpoint = `/api/v1/internal/jobs/${job.id}/complete`;
  assert.equal((await worker.fetch(request(endpoint, "POST", completion, internal), env)).status, 200);
  assert.equal((await worker.fetch(request(endpoint, "POST", completion, internal), env)).status, 200);
  let detail = await (await worker.fetch(request(`/api/v1/watches/${watchId}`, "GET", null, headers), env)).json();
  assert.equal(detail.last_outcome, "NO_MATCH");
  assert.equal(detail.history.length, 1);
  assert.equal(detail.history[0].event_type, "INITIAL_CHECK");
  assert.equal(detail.coverage.checked, 2);
  sqlite.prepare("UPDATE watches SET next_check_at=? WHERE id=?").run("2020-01-02T00:00:00.000Z", watchId);
  await worker.scheduled({ cron: "*/15 * * * *" }, env);
  const next = (await (await worker.fetch(request("/api/v1/internal/jobs/claim", "POST", { module: "family-deals", limit: 1 }, internal), env)).json()).jobs[0];
  assert.ok(next);
  assert.equal((await worker.fetch(request(`/api/v1/internal/jobs/${next.id}/complete`, "POST", { ...completion, claim_id: next.claim_id }, internal), env)).status, 200);
  detail = await (await worker.fetch(request(`/api/v1/watches/${watchId}`, "GET", null, headers), env)).json();
  assert.equal(detail.history.length, 1);

  const requested = await worker.fetch(request(`/api/v1/watches/${watchId}/check`, "POST", {}, headers), env);
  assert.equal(requested.status, 202);
  const third = (await (await worker.fetch(request("/api/v1/internal/jobs/claim", "POST", { module: "family-deals", limit: 1 }, internal), env)).json()).jobs[0];
  const item = { id: crypto.randomUUID(), title: "Possible family meal", outcome: "PARTIAL",
    verification: "PARTIALLY_VERIFIED", fingerprint: "stable-meal", summary: "Location applicability unknown",
    details: { restaurant: "Example", deal_name: null, price_cents: 5000, location_verified: false },
    evidence: [{ source: "Restaurant menu", summary: "A $50 meal for seven", url: "https://example.com/menu" }] };
  assert.equal((await worker.fetch(request(`/api/v1/internal/jobs/${third.id}/results`, "POST",
    { claim_id: third.claim_id, items: [item] }, internal), env)).status, 200);
  assert.equal((await worker.fetch(request(`/api/v1/internal/jobs/${third.id}/complete`, "POST",
    { claim_id: third.claim_id, outcome: "PARTIAL", summary: "Location needs confirmation",
      coverage: { state: "partial", discovered: 2, checked: 2, unavailable: 0, unresolved: 0 } }, internal), env)).status, 200);
  detail = await (await worker.fetch(request(`/api/v1/watches/${watchId}`, "GET", null, headers), env)).json();
  assert.equal(detail.history.length, 2);
  assert.equal(detail.history[0].event_type, "OUTCOME_CHANGED");
  assert.equal(detail.status, "ACTIVE"); // a partial candidate is not a verified match
  assert.ok(detail.current_fingerprint);
  const results = await (await worker.fetch(request(`/api/v1/results?watch_id=${watchId}`, "GET", null, headers), env)).json();
  assert.equal(results.results.length, 1);
});

test("pause blocks claims; resume and stop preserve audit trail", async (t) => {
  const { sqlite, env } = environment(); t.after(() => sqlite.close());
  const headers = await session(env);
  const { watchId } = await createSearchAndWatch(env, headers);
  sqlite.prepare("UPDATE jobs SET status='COMPLETED' WHERE search_id IS NOT NULL").run();
  assert.equal((await worker.fetch(request(`/api/v1/watches/${watchId}/check`, "POST", {}, headers), env)).status, 202);
  assert.equal((await worker.fetch(request(`/api/v1/watches/${watchId}`, "PATCH", { action: "pause" }, headers), env)).status, 200);
  assert.equal((await worker.fetch(request(`/api/v1/watches/${watchId}/check`, "POST", {}, headers), env)).status, 409);
  const internal = { Authorization: `Bearer ${env.WORKER_SECRET}` };
  const claimPath = "/api/v1/internal/jobs/claim";
  assert.deepEqual((await (await worker.fetch(request(claimPath, "POST", { module: "family-deals", limit: 1 }, internal), env)).json()).jobs, []);
  const resumed = await worker.fetch(request(`/api/v1/watches/${watchId}`, "PATCH", { action: "resume" }, headers), env);
  assert.equal(resumed.status, 200);
  assert.ok((await resumed.json()).next_check_at);
  assert.equal((await (await worker.fetch(request(claimPath, "POST", { module: "family-deals", limit: 1 }, internal), env)).json()).jobs[0].watch_id, watchId);
  assert.equal((await worker.fetch(request(`/api/v1/watches/${watchId}`, "DELETE", null, headers), env)).status, 200);
  assert.equal((await worker.fetch(request(`/api/v1/watches/${watchId}/check`, "POST", {}, headers), env)).status, 409);
  assert.equal(sqlite.prepare("SELECT status FROM watches WHERE id=?").get(watchId).status, "STOPPED");
});

test("free-run exhaustion delays Watch and recovers without dispatching a paid run", async (t) => {
  const { sqlite, env } = environment(); t.after(() => sqlite.close());
  const headers = await session(env);
  const { watchId } = await createSearchAndWatch(env, headers);
  sqlite.prepare("UPDATE jobs SET status='COMPLETED' WHERE search_id IS NOT NULL").run();
  const today = new Date().toISOString().slice(0, 10);
  sqlite.prepare("UPDATE dispatch_gate SET utc_day=?,runs_today=1 WHERE id=1").run(today);
  env.DISPATCH_ENABLED = "true";
  env.DISPATCH_DAILY_LIMIT = "1";
  env.GITHUB_DISPATCH_TOKEN = "t".repeat(40);
  const response = await worker.fetch(request(`/api/v1/watches/${watchId}/check`, "POST", {}, headers), env);
  assert.equal(response.status, 202);
  assert.equal((await response.json()).dispatch, "free_capacity");
  assert.equal(sqlite.prepare("SELECT status FROM watches WHERE id=?").get(watchId).status, "DELAYED");
  const pending = sqlite.prepare("SELECT status,delay_reason FROM jobs WHERE watch_id=?").get(watchId);
  assert.equal(pending.status, "DELAYED");
  assert.equal(pending.delay_reason, "free_capacity");
  const tomorrow = new Date(Date.now() + 48 * 60 * 60 * 1000);
  await restoreFreeCapacity(env, tomorrow);
  assert.equal(sqlite.prepare("SELECT status FROM jobs WHERE watch_id=?").get(watchId).status, "QUEUED");
  assert.equal(sqlite.prepare("SELECT status FROM watches WHERE id=?").get(watchId).status, "ACTIVE");
});

test("criteria edits copy a new completed Search and version subsequent history", async (t) => {
  const { sqlite, env } = environment(); t.after(() => sqlite.close());
  const headers = await session(env);
  const { watchId } = await createSearchAndWatch(env, headers);
  const updatedCriteria = { ...criteria, radius_miles: 12, max_total_price: 90 };
  const search = await worker.fetch(request("/api/v1/searches", "POST", { module: "family-deals", criteria: updatedCriteria }, headers), env);
  const searchId = (await search.json()).id;
  sqlite.prepare("UPDATE searches SET status='COMPLETED' WHERE id=?").run(searchId);
  sqlite.prepare("UPDATE jobs SET status='COMPLETED' WHERE search_id IS NOT NULL").run();
  assert.equal((await worker.fetch(request(`/api/v1/watches/${watchId}/check`, "POST", {}, headers), env)).status, 202);
  const edit = { action: "edit_from_search", search_id: searchId };
  assert.equal((await worker.fetch(request(`/api/v1/watches/${watchId}`, "PATCH", edit, headers), env)).status, 409);
  const internal = { Authorization: `Bearer ${env.WORKER_SECRET}` };
  const claimPath = "/api/v1/internal/jobs/claim";
  const first = (await (await worker.fetch(request(claimPath, "POST", { module: "family-deals", limit: 1 }, internal), env)).json()).jobs[0];
  const coverage = { state: "complete", discovered: 1, checked: 1, unavailable: 0, unresolved: 0 };
  assert.equal((await worker.fetch(request(`/api/v1/internal/jobs/${first.id}/complete`, "POST",
    { claim_id: first.claim_id, outcome: "NO_MATCH", summary: "None found", coverage }, internal), env)).status, 200);
  const response = await worker.fetch(request(`/api/v1/watches/${watchId}`, "PATCH", edit, headers), env);
  assert.equal(response.status, 200, await response.text());
  const detail = await (await worker.fetch(request(`/api/v1/watches/${watchId}`, "GET", null, headers), env)).json();
  assert.equal(detail.criteria_version, 2);
  assert.deepEqual(detail.criteria, updatedCriteria);
  assert.deepEqual(detail.criteria_history.map((version) => version.criteria), [updatedCriteria, criteria]);
  assert.equal(detail.history[0].criteria_version, 1);
  assert.equal((await worker.fetch(request(`/api/v1/watches/${watchId}/check`, "POST", {}, headers), env)).status, 202);
  const claimed = (await (await worker.fetch(request(claimPath, "POST", { module: "family-deals", limit: 1 }, internal), env)).json()).jobs[0];
  assert.deepEqual(claimed.criteria, updatedCriteria);
  const completion = { claim_id: claimed.claim_id, outcome: "NO_MATCH", summary: "None found",
    coverage };
  assert.equal((await worker.fetch(request(`/api/v1/internal/jobs/${claimed.id}/complete`, "POST", completion, internal), env)).status, 200);
  const after = await (await worker.fetch(request(`/api/v1/watches/${watchId}`, "GET", null, headers), env)).json();
  assert.equal(after.history[0].criteria_version, 2);
  assert.equal(after.history[1].criteria_version, 1);
});
