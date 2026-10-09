import test from "node:test";
import assert from "node:assert/strict";
import worker from "./worker.mjs";

const base = "https://example.workers.dev";
function environment() {
  const searches = new Map();
  const jobs = new Map();
  const DB = {
    prepare(sql) {
      return {
        bind(...args) {
          return {
            async run() { if (sql.startsWith("INSERT OR IGNORE")) return {}; throw new Error("Unexpected run"); },
            async first() {
              if (sql.startsWith("UPDATE jobs")) { const job = jobs.get(args[2]); if (!job || job.claim_id !== args[3]) return null; job.lease_expires_at = args[0]; return { id: args[2] }; }
              if (sql.includes("SELECT id FROM searches WHERE user_id=? AND module='family-deals'")) {
                return [...searches.values()].find((item) => item.user_id === args[0] && ["QUEUED", "RUNNING"].includes(item.status)) || null;
              }
              assert.match(sql, /user_id=\?/);
              const search = searches.get(args[0]);
              return args[1] === "private-beta" ? (sql.includes("criteria_json") ? (search ? { criteria_json: search.criteria_json, schema_version: 1 } : null) : search || null) : null;
            },
            async all() {
              assert.match(sql, /UPDATE jobs SET status='CLAIMED'/);
              const selected = [...jobs.entries()].filter(([id, job]) => id === args[5] && job.status === "QUEUED").slice(0, 1);
              return { results: selected.map(([id, job]) => { job.status = "CLAIMED"; job.claim_id = args[0]; job.lease_expires_at = args[2]; return { id, user_id: "private-beta", search_id: job.search_id, watch_id: null, module: "family-deals", claim_id: args[0], attempt_number: 1, lease_expires_at: args[2] }; }) };
            },
            sql, args,
          };
        },
      };
    },
    async batch(queries) {
      assert.equal(queries.length, 2);
      if (queries[0].sql.startsWith("INSERT INTO searches")) {
        const search = queries[0].args, job = queries[1].args;
        searches.set(search[0], { id: search[0], user_id: search[1], module: search[2], criteria_json: search[3], status: search[5], last_outcome: null, coverage_json: null, created_at: search[6], updated_at: search[7], completed_at: null });
        jobs.set(job[0], { search_id: job[2], idempotency_key: job[6], status: "QUEUED" });
      } else {
        for (const query of queries) {
          if (query.sql.startsWith("UPDATE searches SET status='FAILED'")) {
            const row = searches.get(query.args[2]);
            if (row) { row.status = "FAILED"; row.last_outcome = "ERROR"; row.completed_at = query.args[1]; }
          } else if (query.sql.startsWith("UPDATE jobs SET status='FAILED'")) {
            const row = jobs.get(query.args[2]);
            if (row) { row.status = "FAILED"; row.delay_reason = query.args[0]; }
          }
        }
      }
      return [{ success: true }, { success: true }];
    },
  };
  return { env: { DB, ACCESS_SECRET: "a".repeat(40), SESSION_KEY: "b".repeat(40), WORKER_SECRET: "c".repeat(40) }, searches, jobs };
}
const request = (path, method = "GET", body, headers = {}) => new Request(`${base}${path}`, { method, headers: { ...(body ? { "Content-Type": "application/json", Origin: base } : {}), ...headers }, ...(body ? { body: JSON.stringify(body) } : {}) });
async function login(env) {
  const response = await worker.fetch(request("/api/v1/session", "POST", { access_secret: env.ACCESS_SECRET }), env);
  assert.equal(response.status, 200);
  const data = await response.json();
  const cookie = response.headers.get("Set-Cookie").split(";")[0];
  return { cookie, csrf: data.csrf_token };
}
const criteria = { schema_version: 1, location: "91304", radius_miles: 2, party_size: 7, max_total_price: 85, cuisines: ["pizza_italian"], restaurant_type: "any", open_tonight: false };

test("scheduled tick is inert before guarded dispatch is configured", async () => {
  const { env } = environment();
  await worker.scheduled({ cron: "*/15 * * * *" }, env);
});

test("system status reports configured on-demand mode without claiming a recurring schedule", async () => {
  const { env } = environment();
  const response = await worker.fetch(request("/api/v1/system/status"), env);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { state: "configured", dispatch: "not_connected", scheduled_checks: false });
  env.DISPATCH_ENABLED = "true";
  env.GITHUB_DISPATCH_TOKEN = "g".repeat(40);
  const ready = await worker.fetch(request("/api/v1/system/status"), env);
  assert.deepEqual(await ready.json(), { state: "configured", dispatch: "ready", scheduled_checks: false });
});

test("session denies wrong secret and origin; cookie is secure", async () => {
  const { env } = environment();
  const unauthenticated = await worker.fetch(request("/api/v1/session"), env);
  assert.equal(unauthenticated.status, 401);
  assert.equal(unauthenticated.headers.get("Set-Cookie"), null);
  assert.equal((await worker.fetch(request("/api/v1/session", "POST", { access_secret: "wrong" }), env)).status, 401);
  assert.equal((await worker.fetch(request("/api/v1/session", "POST", { access_secret: env.ACCESS_SECRET }, { Origin: "https://attacker.example" }), env)).status, 403);
  const { cookie } = await login(env);
  assert.match(cookie, /^__Host-uw_session=/);
  assert.equal((await worker.fetch(request("/api/v1/session", "GET", null, { Cookie: cookie }), env)).status, 200);
});

test("search requires session and CSRF, queues exact criteria without claiming execution", async () => {
  const { env, searches, jobs } = environment();
  assert.equal((await worker.fetch(request("/api/v1/searches", "POST", { module: "family-deals", criteria }), env)).status, 401);
  const { cookie, csrf } = await login(env);
  assert.equal((await worker.fetch(request("/api/v1/searches", "POST", { module: "family-deals", criteria }, { Cookie: cookie }), env)).status, 403);
  const headers = { Cookie: cookie, "X-CSRF-Token": csrf };
  const response = await worker.fetch(request("/api/v1/searches", "POST", { module: "family-deals", criteria }, headers), env);
  assert.equal(response.status, 202);
  const data = await response.json();
  assert.equal(data.status, "QUEUED");
  assert.equal(data.dispatch, "not_connected");
  assert.equal(searches.size, 1);
  assert.equal(jobs.size, 1);
  const duplicate = await worker.fetch(request("/api/v1/searches", "POST", { module: "family-deals", criteria }, headers), env);
  assert.equal(duplicate.status, 409);
  assert.equal(searches.size, 1);
  const detail = await worker.fetch(request(`/api/v1/searches/${data.id}`, "GET", null, { Cookie: cookie }), env);
  assert.equal((await detail.json()).status, "QUEUED");
  assert.equal(detail.status, 200);
});

test("invalid budget and module create no jobs", async () => {
  const { env, jobs } = environment();
  const { cookie, csrf } = await login(env);
  const headers = { Cookie: cookie, "X-CSRF-Token": csrf };
  assert.equal((await worker.fetch(request("/api/v1/searches", "POST", { module: "family-deals", criteria: { ...criteria, max_total_price: 50.005 } }, headers), env)).status, 400);
  assert.equal((await worker.fetch(request("/api/v1/searches", "POST", { module: "movies", criteria }, headers), env)).status, 400);
  assert.equal(jobs.size, 0);
});

test("internal worker claim is authenticated, job-scoped and can renew its lease", async () => {
  const { env, jobs } = environment();
  const { cookie, csrf } = await login(env);
  const search = await worker.fetch(request("/api/v1/searches", "POST", { module: "family-deals", criteria }, { Cookie: cookie, "X-CSRF-Token": csrf }), env);
  assert.equal(search.status, 202);
  const path = "/api/v1/internal/jobs/claim";
  assert.equal((await worker.fetch(request(path, "POST", { limit: 10 }), env)).status, 401);
  const headers = { Authorization: `Bearer ${env.WORKER_SECRET}` };
  const jobId = [...jobs.keys()][0];
  assert.equal((await worker.fetch(request(path, "POST", { limit: 11, module: "family-deals", job_id: jobId }, headers), env)).status, 400);
  assert.equal((await worker.fetch(request(path, "POST", { limit: 1, module: "family-deals" }, headers), env)).status, 400);
  const claimed = await worker.fetch(request(path, "POST", { limit: 1, module: "family-deals", job_id: jobId }, headers), env);
  assert.equal(claimed.status, 200);
  const payload = await claimed.json();
  assert.equal(payload.jobs.length, 1);
  assert.deepEqual(payload.jobs[0].criteria, criteria);
  const second = await worker.fetch(request(path, "POST", { limit: 1, module: "family-deals", job_id: jobId }, headers), env);
  assert.equal(second.status, 200);
  assert.deepEqual((await second.json()).jobs, []);
  const stale = await worker.fetch(request(`/api/v1/internal/jobs/${payload.jobs[0].id}/heartbeat`, "POST", { claim_id: crypto.randomUUID() }, headers), env);
  assert.equal(stale.status, 409);
  const heartbeat = await worker.fetch(request(`/api/v1/internal/jobs/${payload.jobs[0].id}/heartbeat`, "POST", { claim_id: payload.jobs[0].claim_id }, headers), env);
  assert.equal(heartbeat.status, 200);
});

test("static app assets are served even before API secrets are configured", async () => {
  const requestRoot = new Request(base + "/", { method: "GET" });
  const env = { ASSETS: { async fetch(request) {
    assert.equal(new URL(request.url).pathname, "/");
    return new Response("<title>Universal Watcher</title>", { headers: { "Content-Type": "text/html" } });
  } } };
  const response = await worker.fetch(requestRoot, env);
  assert.equal(response.status, 200);
  assert.match(await response.text(), /Universal Watcher/);
});

test("configured dispatch without a token fails the Search instead of leaving it queued", async () => {
  const { env, searches, jobs } = environment();
  env.DISPATCH_ENABLED = "true";
  const { cookie, csrf } = await login(env);
  const response = await worker.fetch(request("/api/v1/searches", "POST", { module: "family-deals", criteria }, { Cookie: cookie, "X-CSRF-Token": csrf }), env);
  assert.equal(response.status, 503);
  const data = await response.json();
  assert.equal(data.dispatch, "not_configured");
  assert.equal(searches.get(data.id).status, "FAILED");
  assert.equal([...jobs.values()][0].status, "FAILED");
});
