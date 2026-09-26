import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import worker from "./worker.mjs";

const base = "https://example.workers.dev";
const criteria = { schema_version: 1, location: "91304", radius_miles: 2,
  party_size: 7, max_total_price: 85, cuisines: [], restaurant_type: "any", open_tonight: false };
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
      try { const result = statements.map(({ sql, args }) => sqlite.prepare(sql).run(...args)); sqlite.exec("COMMIT"); return result; }
      catch (error) { sqlite.exec("ROLLBACK"); throw error; }
    },
  };
  return { sqlite, env: { DB, ACCESS_SECRET: "a".repeat(40), SESSION_KEY: "b".repeat(40), WORKER_SECRET: "c".repeat(40) } };
}
async function createSearch(env) {
  const login = await worker.fetch(request("/api/v1/session", "POST", { access_secret: env.ACCESS_SECRET }), env);
  const headers = { Cookie: login.headers.get("Set-Cookie").split(";")[0], "X-CSRF-Token": (await login.json()).csrf_token };
  const search = await worker.fetch(request("/api/v1/searches", "POST", { module: "family-deals", criteria }, headers), env);
  assert.equal(search.status, 202);
  return { headers, searchId: (await search.json()).id };
}
const internal = (env) => ({ Authorization: `Bearer ${env.WORKER_SECRET}` });
async function claim(env) {
  const response = await worker.fetch(request("/api/v1/internal/jobs/claim", "POST", { module: "family-deals", limit: 1 }, internal(env)), env);
  assert.equal(response.status, 200);
  return (await response.json()).jobs[0];
}

test("execution failures retry twice then stop without declaring no-match", async (t) => {
  const { sqlite, env } = environment(); t.after(() => sqlite.close());
  const { searchId } = await createSearch(env);
  for (let attempt = 1; attempt <= 3; attempt++) {
    const job = await claim(env);
    assert.equal(job.attempt_number, attempt);
    if (attempt === 1) {
      const item = { id: crypto.randomUUID(), outcome: "PARTIAL", verification: "PARTIALLY_VERIFIED",
        title: "Unfinished meal candidate", details: { location_verified: false },
        evidence: [{ source: "Restaurant menu", summary: "Price not fully checked" }] };
      assert.equal((await worker.fetch(request(`/api/v1/internal/jobs/${job.id}/results`, "POST",
        { claim_id: job.claim_id, items: [item] }, internal(env)), env)).status, 200);
      assert.equal(sqlite.prepare("SELECT count(*) AS n FROM results WHERE job_id=?").get(job.id).n, 1);
    }
    const endpoint = `/api/v1/internal/jobs/${job.id}/failure`;
    assert.equal((await worker.fetch(request(endpoint, "POST", { claim_id: crypto.randomUUID(), category: "execution" }, internal(env)), env)).status, 409);
    const response = await worker.fetch(request(endpoint, "POST", { claim_id: job.claim_id, category: "execution" }, internal(env)), env);
    const body = await response.json();
    assert.equal(response.status, 200, JSON.stringify(body));
    assert.equal(body.retry, attempt < 3);
    assert.equal(sqlite.prepare("SELECT count(*) AS n FROM results WHERE job_id=?").get(job.id).n, 0);
    assert.equal((await worker.fetch(request(endpoint, "POST", { claim_id: job.claim_id, category: "execution" }, internal(env)), env)).status, 409);
    if (attempt < 3) sqlite.prepare("UPDATE jobs SET due_at=? WHERE id=?").run("2020-01-01T00:00:00.000Z", job.id);
  }
  assert.equal(sqlite.prepare("SELECT status FROM jobs WHERE search_id=?").get(searchId).status, "FAILED");
  const row = sqlite.prepare("SELECT status,last_outcome FROM searches WHERE id=?").get(searchId);
  assert.equal(row.status, "FAILED");
  assert.equal(row.last_outcome, "ERROR");
  assert.equal(await claim(env), undefined);
});

test("expired third lease pauses Watch with a single failure-history event", async (t) => {
  const { sqlite, env } = environment(); t.after(() => sqlite.close());
  const { headers, searchId } = await createSearch(env);
  sqlite.prepare("UPDATE searches SET status='COMPLETED' WHERE id=?").run(searchId);
  sqlite.prepare("UPDATE jobs SET status='COMPLETED' WHERE search_id=?").run(searchId);
  const watch = await worker.fetch(request("/api/v1/watches", "POST", { search_id: searchId }, headers), env);
  const watchId = (await watch.json()).id;
  assert.equal((await worker.fetch(request(`/api/v1/watches/${watchId}/check`, "POST", {}, headers), env)).status, 202);
  const job = await claim(env);
  sqlite.prepare("UPDATE jobs SET attempt_number=3,lease_expires_at=? WHERE id=?").run("2020-01-01T00:00:00.000Z", job.id);
  await worker.scheduled({ cron: "*/15 * * * *" }, env);
  await worker.scheduled({ cron: "*/15 * * * *" }, env);
  const detail = await (await worker.fetch(request(`/api/v1/watches/${watchId}`, "GET", null, headers), env)).json();
  assert.equal(sqlite.prepare("SELECT status FROM jobs WHERE id=?").get(job.id).status, "FAILED");
  assert.equal(detail.status, "PAUSED");
  assert.equal(detail.last_outcome, "ERROR");
  assert.equal(detail.history.length, 1);
  assert.equal(detail.history[0].event_type, "EXECUTION_FAILED");
});

test("provider failure stays unavailable and does not retry automatically", async (t) => {
  const { sqlite, env } = environment(); t.after(() => sqlite.close());
  const { searchId } = await createSearch(env);
  const job = await claim(env);
  const failure = await worker.fetch(request(`/api/v1/internal/jobs/${job.id}/failure`, "POST",
    { claim_id: job.claim_id, category: "provider" }, internal(env)), env);
  assert.equal(failure.status, 200);
  assert.equal((await failure.json()).retry, false);
  assert.equal(sqlite.prepare("SELECT last_outcome FROM searches WHERE id=?").get(searchId).last_outcome, "UNAVAILABLE");
});

test("reclaiming a crashed lease clears partial chunks before a new attempt", async (t) => {
  const { sqlite, env } = environment(); t.after(() => sqlite.close());
  await createSearch(env);
  const first = await claim(env);
  const item = { id: crypto.randomUUID(), outcome: "PARTIAL", verification: "PARTIALLY_VERIFIED",
    title: "Stale meal", details: { location_verified: false },
    evidence: [{ source: "Restaurant menu", summary: "Incomplete evidence" }] };
  assert.equal((await worker.fetch(request(`/api/v1/internal/jobs/${first.id}/results`, "POST",
    { claim_id: first.claim_id, items: [item] }, internal(env)), env)).status, 200);
  sqlite.prepare("UPDATE jobs SET lease_expires_at=? WHERE id=?").run("2020-01-01T00:00:00.000Z", first.id);
  const second = await claim(env);
  assert.equal(second.attempt_number, 2);
  assert.equal(sqlite.prepare("SELECT count(*) AS n FROM results WHERE job_id=?").get(first.id).n, 0);
  assert.equal(sqlite.prepare("SELECT count(*) AS n FROM result_evidence WHERE result_id=?").get(item.id).n, 0);
});
