import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { dispatchPending, restoreFreeCapacity } from "./dispatch.mjs";

const jobId = "00000000-0000-4000-8000-000000000001";

function environment() {
  const sqlite = new DatabaseSync(":memory:");
  for (const migration of ["0001_initial.sql", "0002_dispatch_gate.sql"])
    sqlite.exec(readFileSync(new URL(`./migrations/${migration}`, import.meta.url), "utf8"));
  sqlite.prepare("INSERT INTO users(id,created_at) VALUES (?,?)").run("u", "2026-09-26T00:00:00.000Z");
  sqlite.prepare("INSERT INTO searches(id,user_id,module,criteria_json,schema_version,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)")
    .run("s", "u", "family-deals", "{}", 1, "QUEUED", "2026-09-26T00:00:00.000Z", "2026-09-26T00:00:00.000Z");
  sqlite.prepare("INSERT INTO jobs(id,user_id,search_id,module,status,due_at,idempotency_key,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)")
    .run(jobId, "u", "s", "family-deals", "QUEUED", "2026-09-26T00:00:00.000Z", "search:s", "2026-09-26T00:00:00.000Z", "2026-09-26T00:00:00.000Z");
  const DB = {
    prepare(sql) { return { bind(...args) { return { sql, args,
      async first() { return sqlite.prepare(sql).get(...args) || null; },
      async run() { return sqlite.prepare(sql).run(...args); },
    }; } }; },
    async batch(statements) {
      sqlite.exec("BEGIN");
      try { const output = statements.map(({ sql, args }) => sqlite.prepare(sql).run(...args)); sqlite.exec("COMMIT"); return output; }
      catch (error) { sqlite.exec("ROLLBACK"); throw error; }
    },
  };
  return { sqlite, env: { DB, DISPATCH_ENABLED: "true", DISPATCH_DAILY_LIMIT: "10", GITHUB_DISPATCH_TOKEN: "t".repeat(40) } };
}

test("dispatch sends only a work signal and respects cooldown and daily reservation", async (t) => {
  const { sqlite, env } = environment();
  t.after(() => sqlite.close());
  const requests = [];
  const oldFetch = globalThis.fetch;
  globalThis.fetch = async (url, options) => { requests.push({ url, options }); return { status: 204 }; };
  t.after(() => { globalThis.fetch = oldFetch; });
  const time = new Date("2026-09-26T01:00:00.000Z");
  assert.equal(await dispatchPending(env, time, jobId), "signaled");
  for (let minute = 1; minute < 10; minute++) {
    assert.equal(await dispatchPending(env, new Date(`2026-09-26T01:${String(minute).padStart(2, "0")}:00.000Z`), jobId), "signaled");
  }
  assert.equal(await dispatchPending(env, new Date("2026-09-26T01:10:00.000Z"), jobId), "free_capacity");
  assert.equal(requests.length, 10);
  assert.deepEqual(JSON.parse(requests[0].options.body), { ref: "main", inputs: { job_id: jobId } });
  assert.match(requests[0].url, /family-deals-worker\.yml\/dispatches$/);
  assert.equal(sqlite.prepare("SELECT runs_today FROM dispatch_gate").get().runs_today, 10);
  const delayed = sqlite.prepare("SELECT status,delay_reason FROM jobs WHERE id=?").get(jobId);
  assert.equal(delayed.status, "DELAYED");
  assert.equal(delayed.delay_reason, "free_capacity");
  assert.equal(sqlite.prepare("SELECT status FROM searches WHERE id='s'").get().status, "DELAYED");
  await restoreFreeCapacity(env, new Date("2026-09-27T01:00:00.000Z"));
  assert.equal(sqlite.prepare("SELECT status FROM searches WHERE id='s'").get().status, "QUEUED");
  assert.equal(await dispatchPending(env, new Date("2026-09-27T01:00:00.000Z"), jobId), "signaled");
  assert.equal(requests.length, 11);
});

test("current GitHub API 200 dispatch response is accepted", async (t) => {
  const { sqlite, env } = environment();
  t.after(() => sqlite.close());
  const oldFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls++; return { status: 200, text: async () => '{"workflow_run_id":123}' }; };
  t.after(() => { globalThis.fetch = oldFetch; });
  assert.equal(await dispatchPending(env, new Date("2026-09-26T01:00:00.000Z"), jobId), "signaled");
  assert.equal(calls, 1);
});

test("disabled dispatch never contacts GitHub; failed dispatch stays queued with conservative reservation", async (t) => {
  const { sqlite, env } = environment();
  t.after(() => sqlite.close());
  const oldFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls++; throw new Error("temporary failure"); };
  t.after(() => { globalThis.fetch = oldFetch; });
  env.DISPATCH_ENABLED = "false";
  assert.equal(await dispatchPending(env, new Date(), jobId), "not_connected");
  env.DISPATCH_ENABLED = "true";
  assert.equal(await dispatchPending(env, new Date("2026-09-26T01:00:00.000Z"), jobId), "dispatch_network");
  assert.equal(calls, 1);
  assert.equal(sqlite.prepare("SELECT status FROM jobs WHERE id=?").get(jobId).status, "QUEUED");
  assert.equal(sqlite.prepare("SELECT runs_today FROM dispatch_gate").get().runs_today, 1);
});

test("an expired claimed lease is signaled for recovery", async (t) => {
  const { sqlite, env } = environment(); t.after(() => sqlite.close());
  sqlite.prepare("UPDATE jobs SET status='CLAIMED',lease_expires_at=? WHERE id=?").run("2026-09-26T00:30:00.000Z", jobId);
  const oldFetch = globalThis.fetch;
  let signals = 0;
  globalThis.fetch = async () => { signals++; return { status: 204 }; };
  t.after(() => { globalThis.fetch = oldFetch; });
  assert.equal(await dispatchPending(env, new Date("2026-09-26T01:00:00.000Z"), jobId), "signaled");
  assert.equal(signals, 1);
});
