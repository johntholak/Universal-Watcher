import { validateFamilyDealsCriteria } from "./criteria.mjs";
import { validateResultChunk, verifyFamilyMatch, validateCompletion, digest } from "./results.mjs";
import { dispatchPending, expireExhaustedJobs, restoreFreeCapacity } from "./dispatch.mjs";
import { nextWatchCheck, queueDueWatches } from "./watches.mjs";

const COOKIE = "__Host-uw_session";
const MAX_BODY_BYTES = 4096;
const SESSION_SECONDS = 7 * 24 * 60 * 60;
const json = (data, status = 200, headers = {}) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...headers } });
const now = () => new Date().toISOString();

async function hmac(secret, value) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value)));
}
function encode(bytes) { return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); }
function equal(a, b) { if (a.length !== b.length) return false; let difference = 0; for (let i = 0; i < a.length; i++) difference |= a.charCodeAt(i) ^ b.charCodeAt(i); return difference === 0; }
function cookieValue(request) { const item = request.headers.get("Cookie")?.split("; ").find((part) => part.startsWith(`${COOKIE}=`)); return item?.slice(COOKIE.length + 1) || ""; }
function sameOrigin(request) { return request.headers.get("Origin") === new URL(request.url).origin; }
function requireConfig(env) { return env?.DB && typeof env.ACCESS_SECRET === "string" && env.ACCESS_SECRET.length >= 32 && typeof env.SESSION_KEY === "string" && env.SESSION_KEY.length >= 32; }
async function workerAuthorized(request, env) {
  const secret = env.WORKER_SECRET;
  if (typeof secret !== "string" || secret.length < 32) return false;
  const header = request.headers.get("Authorization") || "";
  if (!header.startsWith("Bearer ")) return false;
  return equal(encode(await hmac(secret, header.slice(7))), encode(await hmac(secret, secret)));
}

async function session(request, env) {
  const token = cookieValue(request);
  const [value, signature] = token.split(".");
  if (!value || !signature || !equal(signature, encode(await hmac(env.SESSION_KEY, value)))) return null;
  try {
    const data = JSON.parse(atob(value.replace(/-/g, "+").replace(/_/g, "/")));
    return data.user_id === "private-beta" && Number.isSafeInteger(data.exp) && data.exp > Date.now() ? { token, user_id: data.user_id } : null;
  } catch { return null; }
}
async function csrf(env, token) { return encode(await hmac(env.SESSION_KEY, `csrf:${token}`)); }
async function bodyObject(request, maxBytes = MAX_BODY_BYTES) {
  const length = Number(request.headers.get("Content-Length") || 0);
  if (length > maxBytes) throw new Error("Request is too large");
  const body = await request.text();
  if (new TextEncoder().encode(body).length > maxBytes) throw new Error("Request is too large");
  const object = JSON.parse(body);
  if (!object || typeof object !== "object" || Array.isArray(object)) throw new Error("Expected a JSON object");
  return object;
}

function movieViewerPayload(input) {
  const viewerId = typeof input.viewer_id === "string" ? input.viewer_id.trim() : "";
  const displayName = typeof input.display_name === "string" ? input.display_name.trim() : "";
  if (!viewerId || viewerId.length > 80 || !displayName || displayName.length > 120) throw new Error("Viewer requires an ID and display name");
  const weight = Number(input.weight ?? 1);
  if (!Number.isFinite(weight) || weight < 0 || weight > 10) throw new Error("Viewer weight must be between 0 and 10");
  const list = (value, max, label) => {
    if (value == null) return [];
    if (!Array.isArray(value) || value.length > max) throw new Error(label + " must be a list");
    const values = [...new Set(value.filter((item) => typeof item === "string").map((item) => item.trim()).filter(Boolean))];
    if (values.some((item) => item.length > 80)) throw new Error(label + " contains an item that is too long");
    return values;
  };
  const preferredGenres = list(input.preferred_genres, 20, "Preferred genres");
  const dislikedGenres = list(input.disliked_genres, 20, "Disliked genres");
  const preferredKeywords = list(input.preferred_keywords, 20, "Preferred keywords");
  const dislikedKeywords = list(input.disliked_keywords, 20, "Disliked keywords");
  const runtimeMin = input.preferred_runtime_min == null || input.preferred_runtime_min === "" ? null : Number(input.preferred_runtime_min);
  const runtimeMax = input.preferred_runtime_max == null || input.preferred_runtime_max === "" ? null : Number(input.preferred_runtime_max);
  if ((runtimeMin != null && (!Number.isInteger(runtimeMin) || runtimeMin < 1 || runtimeMin > 600)) ||
      (runtimeMax != null && (!Number.isInteger(runtimeMax) || runtimeMax < 1 || runtimeMax > 600))) throw new Error("Preferred runtime must be between 1 and 600 minutes");
  if (runtimeMin != null && runtimeMax != null && runtimeMin > runtimeMax) throw new Error("Preferred runtime minimum cannot exceed maximum");
  return { viewerId, displayName, weight, preferredGenres, dislikedGenres, preferredKeywords, dislikedKeywords, runtimeMin, runtimeMax };
}

export default {
  async scheduled(_controller, env) {
    if (!requireConfig(env)) return;
    try { await expireExhaustedJobs(env); await restoreFreeCapacity(env); await queueDueWatches(env); } catch { /* Next tick retries queued work. */ }
  },
  async fetch(request, env) {
    if (!requireConfig(env)) return json({ error: "Service is not configured" }, 503);
    const url = new URL(request.url);
    const path = url.pathname;
    const legacyMovieSearch = path === "/api/movies/search";
    if (!path.startsWith("/api/v1/") && !legacyMovieSearch) {
      if (request.method === "GET" && env.ASSETS) {
        const asset = await env.ASSETS.fetch(request);
        const headers = new Headers(asset.headers);
        if (path === "/" || path.endsWith(".html") || path.endsWith(".js") || path.endsWith(".css")) {
          headers.set("Cache-Control", "no-store");
        }
        return new Response(asset.body, { status: asset.status, statusText: asset.statusText, headers });
      }
      return json({ error: "Not found" }, 404);
    }
    if (request.method === "GET" && path === "/api/v1/system/status") return json({ state: "production", execution: env.DISPATCH_ENABLED === "true" && typeof env.GITHUB_DISPATCH_TOKEN === "string" && env.GITHUB_DISPATCH_TOKEN.length >= 20 ? "connected" : "not_connected" });

    if (request.method === "POST" && path === "/api/v1/session") {
      if (!sameOrigin(request)) return json({ error: "Invalid origin" }, 403);
      let input; try { input = await bodyObject(request); } catch { return json({ error: "Invalid request" }, 400); }
      if (typeof input.access_secret !== "string" || !equal(encode(await hmac(env.ACCESS_SECRET, input.access_secret)), encode(await hmac(env.ACCESS_SECRET, env.ACCESS_SECRET)))) return json({ error: "Access denied" }, 401);
      const expires = Date.now() + SESSION_SECONDS * 1000;
      const value = encode(new TextEncoder().encode(JSON.stringify({ user_id: "private-beta", exp: expires, nonce: crypto.randomUUID() })));
      const token = `${value}.${encode(await hmac(env.SESSION_KEY, value))}`;
      const stamp = now();
      try { await env.DB.prepare("INSERT OR IGNORE INTO users(id,created_at) VALUES (?,?)").bind("private-beta", stamp).run(); } catch { /* Demo session remains usable for read-only Movie GM searches. */ }
      return json({ authenticated: true, csrf_token: await csrf(env, token) }, 200, { "Set-Cookie": `${COOKIE}=${token}; Path=/; Max-Age=${SESSION_SECONDS}; HttpOnly; Secure; SameSite=Strict` });
    }

    if (path.startsWith("/api/v1/internal/")) {
      if (!(await workerAuthorized(request, env))) return json({ error: "Worker authentication required" }, 401);
      if (request.method === "GET" && path === "/api/v1/internal/jobs/state") {
        try {
          const counts = await env.DB.prepare(`SELECT status,delay_reason,count(*) AS count
            FROM jobs WHERE module='family-deals' GROUP BY status,delay_reason ORDER BY status,delay_reason`).all();
          const recent = await env.DB.prepare(`SELECT id,status,delay_reason,attempt_number,due_at,updated_at,search_id,watch_id
            FROM jobs WHERE module='family-deals' ORDER BY updated_at DESC,id DESC LIMIT 10`).all();
          const searches = await env.DB.prepare(`SELECT id,status,last_outcome,updated_at,completed_at
            FROM searches WHERE module='family-deals' ORDER BY updated_at DESC,id DESC LIMIT 10`).all();
          return json({ counts: counts.results || [], recent_jobs: recent.results || [], recent_searches: searches.results || [] });
        } catch {
          return json({ error: "Worker state unavailable" }, 503);
        }
      }
      if (request.method === "POST" && path === "/api/v1/internal/jobs/claim") {
        let input; try { input = await bodyObject(request); } catch { return json({ error: "Invalid request" }, 400); }
        const limit = input.limit ?? 10;
        if (!Number.isInteger(limit) || limit < 1 || limit > 10) return json({ error: "Batch limit must be 1 through 10" }, 400);
        const module = input.module;
        if (module !== "family-deals") return json({ error: "Unsupported worker module" }, 400);
        const stamp = now(), expires = new Date(Date.now() + 5 * 60 * 1000).toISOString(), claimId = crypto.randomUUID();
        try {
          const claimed = await env.DB.prepare(`UPDATE jobs SET status='CLAIMED', claim_id=?, claimed_at=?, lease_expires_at=?, attempt_number=attempt_number+1, updated_at=?
            WHERE id IN (SELECT j.id FROM jobs j LEFT JOIN watches w ON w.id=j.watch_id
            WHERE j.module=? AND (j.watch_id IS NULL OR w.status IN ('ACTIVE','FOUND')
              OR (w.status='DELAYED' AND j.status IN ('RETRYABLE','CLAIMED','RUNNING')))
              AND j.attempt_number<3
              AND ((j.status IN ('QUEUED','RETRYABLE') AND j.due_at<=?) OR (j.status IN ('CLAIMED','RUNNING') AND j.lease_expires_at<?))
            ORDER BY j.due_at,j.id LIMIT ?) RETURNING id,user_id,search_id,watch_id,module,claim_id,attempt_number,lease_expires_at`).bind(claimId, stamp, expires, stamp, module, stamp, stamp, limit).all();
          const jobs = [];
          for (const row of claimed.results || []) {
            if (row.attempt_number > 1) await env.DB.batch([
              env.DB.prepare(`DELETE FROM result_evidence WHERE result_id IN
                (SELECT r.id FROM results r JOIN jobs j ON j.id=r.job_id WHERE r.job_id=? AND j.claim_id=? AND j.status='CLAIMED')`)
                .bind(row.id, row.claim_id),
              env.DB.prepare(`DELETE FROM results WHERE job_id=? AND EXISTS
                (SELECT 1 FROM jobs WHERE id=? AND claim_id=? AND status='CLAIMED')`)
                .bind(row.id, row.id, row.claim_id),
            ]);
            const source = row.search_id ? await env.DB.prepare("SELECT criteria_json,schema_version FROM searches WHERE id=? AND user_id=?").bind(row.search_id, row.user_id).first() : await env.DB.prepare("SELECT criteria_json,schema_version FROM watches WHERE id=? AND user_id=?").bind(row.watch_id, row.user_id).first();
            if (!source) throw new Error("Missing job source");
            jobs.push({ id: row.id, module: row.module, search_id: row.search_id, watch_id: row.watch_id, claim_id: row.claim_id, attempt_number: row.attempt_number, lease_expires_at: row.lease_expires_at, criteria: JSON.parse(source.criteria_json) });
          }
          return json({ jobs });
        } catch { return json({ error: "Job claim unavailable; retry after checking service state" }, 503); }
      }
      const heartbeat = /^\/api\/v1\/internal\/jobs\/([0-9a-f-]{36})\/heartbeat$/.exec(path);
      if (request.method === "POST" && heartbeat) {
        let input; try { input = await bodyObject(request); } catch { return json({ error: "Invalid request" }, 400); }
        if (typeof input.claim_id !== "string" || !/^[0-9a-f-]{36}$/.test(input.claim_id)) return json({ error: "Invalid claim ID" }, 400);
        const stamp = now(), expires = new Date(Date.now() + 5 * 60 * 1000).toISOString();
        try {
          const updated = await env.DB.prepare("UPDATE jobs SET status='RUNNING', lease_expires_at=?, updated_at=? WHERE id=? AND claim_id=? AND status IN ('CLAIMED','RUNNING') AND lease_expires_at>=? RETURNING id").bind(expires, stamp, heartbeat[1], input.claim_id, stamp).first();
          return updated ? json({ lease_expires_at: expires }) : json({ error: "Claim is no longer active" }, 409);
        } catch { return json({ error: "Lease renewal unavailable" }, 503); }
      }
      const chunk = /^\/api\/v1\/internal\/jobs\/([0-9a-f-]{36})\/results$/.exec(path);
      if (request.method === "POST" && chunk) {
        let input; try { input = validateResultChunk(await bodyObject(request, 32_768)); } catch (error) { return json({ error: error.message }, 400); }
        const stamp = now();
        try {
          const job = await env.DB.prepare("SELECT id,user_id,search_id,watch_id,module,status,claim_id,lease_expires_at FROM jobs WHERE id=?").bind(chunk[1]).first();
          if (!job || job.claim_id !== input.claim_id || !["CLAIMED", "RUNNING"].includes(job.status) || job.lease_expires_at < stamp) return json({ error: "Claim is no longer active" }, 409);
          const source = job.search_id ? await env.DB.prepare("SELECT criteria_json FROM searches WHERE id=? AND user_id=?").bind(job.search_id, job.user_id).first() : await env.DB.prepare("SELECT criteria_json FROM watches WHERE id=? AND user_id=?").bind(job.watch_id, job.user_id).first();
          if (!source) return json({ error: "Job criteria unavailable" }, 409);
          const criteria = JSON.parse(source.criteria_json);
          if (job.module === "family-deals") {
            try { input.items.forEach((item) => verifyFamilyMatch(item, criteria)); }
            catch (error) { return json({ error: error.message }, 400); }
          }
          const statements = [];
          const expected = [];
          for (const item of input.items) {
            const hash = await digest(item);
            expected.push([item.id, hash]);
            statements.push(env.DB.prepare(`INSERT OR IGNORE INTO results(id,user_id,job_id,search_id,watch_id,module,outcome,verification,title,summary,details_json,fingerprint,payload_digest,destination_url,observed_at,created_at)
              SELECT ?,user_id,id,search_id,watch_id,module,?,?,?,?,?,?,?,?,?,? FROM jobs WHERE id=? AND claim_id=? AND status IN ('CLAIMED','RUNNING') AND lease_expires_at>=?`)
              .bind(item.id, item.outcome, item.verification, item.title, item.summary, JSON.stringify(item.details), item.fingerprint, hash, item.destination_url, stamp, stamp, job.id, input.claim_id, stamp));
            for (let index = 0; index < item.evidence.length; index++) {
              const entry = item.evidence[index];
              statements.push(env.DB.prepare(`INSERT OR IGNORE INTO result_evidence(id,user_id,result_id,source,source_url,summary,captured_at)
                SELECT ?,user_id,id,?,?,?,? FROM results WHERE id=? AND job_id=? AND payload_digest=?`)
                .bind(`${item.id}:e${index}`, entry.source, entry.url, entry.summary, entry.captured_at || stamp, item.id, job.id, hash));
            }
          }
          await env.DB.batch(statements);
          for (const [id, hash] of expected) {
            const row = await env.DB.prepare("SELECT payload_digest FROM results WHERE id=? AND job_id=? AND user_id=?").bind(id, job.id, job.user_id).first();
            if (!row || row.payload_digest !== hash) return json({ error: "Conflicting or expired result submission" }, 409);
          }
          return json({ accepted: expected.length });
        } catch { return json({ error: "Result storage unavailable; retry same IDs" }, 503); }
      }
      const complete = /^\/api\/v1\/internal\/jobs\/([0-9a-f-]{36})\/complete$/.exec(path);
      if (request.method === "POST" && complete) {
        let input; try { input = await bodyObject(request); } catch { return json({ error: "Invalid request" }, 400); }
        try {
          const job = await env.DB.prepare("SELECT id,user_id,search_id,watch_id,status,claim_id,lease_expires_at,final_digest FROM jobs WHERE id=?").bind(complete[1]).first();
          if (!job || job.claim_id !== input.claim_id) return json({ error: "Claim unavailable" }, 409);
          const counted = await env.DB.prepare("SELECT count(*) AS total FROM results WHERE job_id=? AND user_id=? AND outcome='MATCH' AND verification='VERIFIED'").bind(job.id, job.user_id).first();
          const normalized = validateCompletion(input, counted?.total || 0);
          const hash = await digest(normalized);
          if (job.final_digest) return job.final_digest === hash ? json({ finalized: true, idempotent: true }) : json({ error: "Conflicting completion" }, 409);
          const stamp = now();
          if (!["CLAIMED", "RUNNING"].includes(job.status) || job.lease_expires_at < stamp) return json({ error: "Claim is no longer active" }, 409);
          const jobState = normalized.outcome === "ERROR" ? "FAILED" : "COMPLETED";
          const statements = [
            env.DB.prepare(`UPDATE jobs SET status=?,final_digest=?,lease_expires_at=NULL,updated_at=?
              WHERE id=? AND claim_id=? AND status IN ('CLAIMED','RUNNING') AND lease_expires_at>=?`).bind(jobState, hash, stamp, job.id, normalized.claim_id, stamp),
          ];
          if (job.search_id) {
            const searchState = normalized.outcome === "ERROR" ? "FAILED" : "COMPLETED";
            statements.push(env.DB.prepare(`UPDATE searches SET status=?,last_outcome=?,coverage_json=?,updated_at=?,completed_at=?
              WHERE id=? AND user_id=? AND EXISTS (SELECT 1 FROM jobs WHERE id=? AND final_digest=?)`)
              .bind(searchState, normalized.outcome, JSON.stringify(normalized.coverage), stamp, stamp, job.search_id, job.user_id, job.id, hash));
          } else if (job.watch_id) {
            const watch = await env.DB.prepare("SELECT status,last_outcome,current_fingerprint,coverage_json FROM watches WHERE id=? AND user_id=?")
              .bind(job.watch_id, job.user_id).first();
            if (!watch) return json({ error: "Watch unavailable" }, 409);
            const records = await env.DB.prepare("SELECT fingerprint FROM results WHERE job_id=? AND user_id=? ORDER BY fingerprint,id")
              .bind(job.id, job.user_id).all();
            const fingerprint = records.results?.length ? await digest(records.results.map((row) => row.fingerprint)) : null;
            const coverage = JSON.stringify(normalized.coverage);
            const event = watch.last_outcome == null ? "INITIAL_CHECK" :
              watch.last_outcome !== normalized.outcome ? "OUTCOME_CHANGED" :
              watch.current_fingerprint !== fingerprint ? "RESULTS_CHANGED" :
              watch.coverage_json !== coverage ? "COVERAGE_CHANGED" : null;
            const next = nextWatchCheck(new Date(stamp));
            statements.push(env.DB.prepare(`UPDATE watches SET status=CASE
                WHEN status IN ('PAUSED','STOPPED') THEN status
                WHEN ? > 0 THEN 'FOUND' ELSE 'ACTIVE' END,
              last_outcome=?,last_checked_at=?,next_check_at=CASE WHEN status IN ('PAUSED','STOPPED') THEN next_check_at ELSE ? END,
              current_fingerprint=?,coverage_json=?,updated_at=?
              WHERE id=? AND user_id=? AND EXISTS (SELECT 1 FROM jobs WHERE id=? AND final_digest=?)`)
              .bind(counted?.total || 0, normalized.outcome, stamp, next, fingerprint, coverage, stamp, job.watch_id, job.user_id, job.id, hash));
            if (event) statements.push(env.DB.prepare(`INSERT INTO watch_runs(id,user_id,watch_id,job_id,event_type,outcome,fingerprint,summary,criteria_version,created_at)
              SELECT ?,user_id,id,?,?,?,?,?,criteria_version,? FROM watches WHERE id=? AND user_id=?
              AND EXISTS (SELECT 1 FROM jobs WHERE id=? AND final_digest=?)`)
              .bind(crypto.randomUUID(), job.id, event, normalized.outcome, fingerprint, normalized.summary, stamp, job.watch_id, job.user_id, job.id, hash));
          } else return json({ error: "Job source unavailable" }, 409);
          await env.DB.batch(statements);
          const finalized = await env.DB.prepare("SELECT final_digest FROM jobs WHERE id=? AND user_id=?").bind(job.id, job.user_id).first();
          return finalized?.final_digest === hash ? json({ finalized: true, idempotent: false }) : json({ error: "Completion raced with another claim" }, 409);
        } catch (error) { return error.status === 400 ? json({ error: error.message }, 400) : json({ error: "Finalization unavailable; retry same completion" }, 503); }
      }
      const failure = /^\/api\/v1\/internal\/jobs\/([0-9a-f-]{36})\/failure$/.exec(path);
      if (request.method === "POST" && failure) {
        let input; try { input = await bodyObject(request); } catch { return json({ error: "Invalid request" }, 400); }
        if (!/^[0-9a-f-]{36}$/.test(input.claim_id || "") || !["execution", "provider"].includes(input.category)) return json({ error: "Invalid failure report" }, 400);
        try {
          const job = await env.DB.prepare("SELECT id,user_id,search_id,watch_id,status,claim_id,lease_expires_at,attempt_number FROM jobs WHERE id=?")
            .bind(failure[1]).first();
          const stamp = now();
          if (!job || job.claim_id !== input.claim_id || !["CLAIMED", "RUNNING"].includes(job.status) || job.lease_expires_at < stamp) return json({ error: "Claim is no longer active" }, 409);
          const retry = input.category === "execution" && job.attempt_number < 3;
          const outcome = input.category === "provider" ? "UNAVAILABLE" : "ERROR";
          const summary = input.category === "provider" ? "Provider unavailable; no match claim made." : "Execution stopped before verification completed.";
          // Interactive Searches retry immediately. Saved Watches retain bounded backoff.
          const due = job.search_id
            ? stamp
            : new Date(Date.now() + job.attempt_number * 30 * 60 * 1000).toISOString();
          const state = retry ? "RETRYABLE" : "FAILED";
          const statements = [env.DB.prepare(`UPDATE jobs SET status=?,due_at=?,delay_reason=?,claim_id=NULL,lease_expires_at=NULL,updated_at=?
            WHERE id=? AND claim_id=? AND status IN ('CLAIMED','RUNNING') AND lease_expires_at>=?`)
            .bind(state, due, input.category, stamp, job.id, input.claim_id, stamp)];
          statements.push(env.DB.prepare(`DELETE FROM result_evidence WHERE result_id IN
            (SELECT r.id FROM results r JOIN jobs j ON j.id=r.job_id WHERE r.job_id=? AND j.status=? AND j.delay_reason=?)`)
            .bind(job.id, state, input.category));
          statements.push(env.DB.prepare(`DELETE FROM results WHERE job_id=? AND EXISTS
            (SELECT 1 FROM jobs WHERE id=? AND status=? AND delay_reason=?)`)
            .bind(job.id, job.id, state, input.category));
          if (job.search_id) statements.push(env.DB.prepare(`UPDATE searches SET status=?,last_outcome=?,updated_at=?
            WHERE id=? AND user_id=? AND EXISTS (SELECT 1 FROM jobs WHERE id=? AND status=? AND delay_reason=?)`)
            .bind(retry ? "DELAYED" : "FAILED", outcome, stamp, job.search_id, job.user_id, job.id, state, input.category));
          if (job.watch_id) {
            statements.push(env.DB.prepare(`UPDATE watches SET status=CASE WHEN status IN ('PAUSED','STOPPED') THEN status ELSE ? END,
              last_outcome=?,last_checked_at=?,updated_at=? WHERE id=? AND user_id=?
                AND EXISTS (SELECT 1 FROM jobs WHERE id=? AND status=? AND delay_reason=?)`)
              .bind(retry ? "DELAYED" : "PAUSED", outcome, stamp, stamp, job.watch_id, job.user_id, job.id, state, input.category));
            if (!retry) statements.push(env.DB.prepare(`INSERT OR IGNORE INTO watch_runs(id,user_id,watch_id,job_id,event_type,outcome,summary,criteria_version,created_at)
              SELECT ?,user_id,id,?,'EXECUTION_FAILED',?,?,criteria_version,? FROM watches WHERE id=? AND user_id=?
                AND EXISTS (SELECT 1 FROM jobs WHERE id=? AND status='FAILED' AND delay_reason=?)`)
              .bind(crypto.randomUUID(), job.id, outcome, summary, stamp, job.watch_id, job.user_id, job.id, input.category));
          }
          await env.DB.batch(statements);
          return json({ retry, status: state, due_at: retry ? due : null });
        } catch { return json({ error: "Failure recording unavailable" }, 503); }
      }
      return json({ error: "Internal route not implemented" }, 404);
    }

    const identity = await session(request, env);
    if (!identity && request.method === "GET" && path === "/api/v1/session") {
      const expires = Date.now() + SESSION_SECONDS * 1000;
      const value = encode(new TextEncoder().encode(JSON.stringify({ user_id: "private-beta", exp: expires, nonce: crypto.randomUUID() })));
      const token = value + "." + encode(await hmac(env.SESSION_KEY, value));
      const stamp = now();
      try { await env.DB.prepare("INSERT OR IGNORE INTO users(id,created_at) VALUES (?,?)").bind("private-beta", stamp).run(); }
      catch { return json({ error: "Storage temporarily unavailable" }, 503); }
      return json({ authenticated: true, csrf_token: await csrf(env, token) }, 200, { "Set-Cookie": COOKIE + "=" + token + "; Path=/; Max-Age=" + SESSION_SECONDS + "; HttpOnly; Secure; SameSite=Strict" });
    }
    if (!identity) return json({ error: "Authentication required" }, 401);
    if (request.method === "GET" && path === "/api/v1/session") return json({ authenticated: true, csrf_token: await csrf(env, identity.token) });
    if (request.method !== "GET" && (!sameOrigin(request) || !equal(request.headers.get("X-CSRF-Token") || "", await csrf(env, identity.token)))) return json({ error: "Invalid request token or origin" }, 403);

    if ((path === "/api/v1/movies/search" || path === "/api/movies/search") && request.method === "GET") {
      if (!env.MOVIE_GM) return json({ error: "Movie GM service is not connected" }, 503);
      const mode = url.searchParams.get("mode") || "everyone";
      const query = (url.searchParams.get("query") || "").trim();
      if (!["everyone", "kids", "tonight"].includes(mode)) return json({ error: "Unsupported Movie GM mode" }, 400);
      if (query.length > 200) return json({ error: "Query is too long" }, 400);
      try {
        const downstream = await env.MOVIE_GM.fetch(new Request("https://movie-gm.internal/internal/movie-gm/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: identity.user_id, mode, query }),
        }));
        const payload = await downstream.json();
        return json(payload, downstream.status);
      } catch {
        return json({ error: "Movie GM service is temporarily unavailable" }, 503);
      }
    }

    if (path === "/api/v1/movies/viewers") {
      if (request.method === "GET") {
        try {
          const rows = await env.DB.prepare(`SELECT viewer_id,display_name,weight,preferred_genres_json,disliked_genres_json,preferred_keywords_json,disliked_keywords_json,preferred_runtime_min,preferred_runtime_max,created_at,updated_at
            FROM movie_viewers WHERE user_id=? ORDER BY created_at,viewer_id`).bind(identity.user_id).all();
          return json({ viewers: (rows.results || []).map((row) => ({
            viewer_id: row.viewer_id, display_name: row.display_name, weight: Number(row.weight),
            preferred_genres: JSON.parse(row.preferred_genres_json || "[]"),
            disliked_genres: JSON.parse(row.disliked_genres_json || "[]"),
            preferred_keywords: JSON.parse(row.preferred_keywords_json || "[]"),
            disliked_keywords: JSON.parse(row.disliked_keywords_json || "[]"),
            preferred_runtime_min: row.preferred_runtime_min, preferred_runtime_max: row.preferred_runtime_max,
            created_at: row.created_at, updated_at: row.updated_at
          })) });
        } catch { return json({ error: "Movie GM household profiles unavailable" }, 503); }
      }
      if (request.method === "POST" || request.method === "PUT") {
        let input; try { input = await bodyObject(request); } catch (error) { return json({ error: error.message || "Invalid request" }, 400); }
        let viewer; try { viewer = movieViewerPayload(input); } catch (error) { return json({ error: error.message }, 400); }
        const stamp = now();
        try {
          const count = await env.DB.prepare("SELECT COUNT(*) AS total FROM movie_viewers WHERE user_id=?").bind(identity.user_id).first();
          const exists = await env.DB.prepare("SELECT viewer_id,created_at FROM movie_viewers WHERE user_id=? AND viewer_id=?").bind(identity.user_id, viewer.viewerId).first();
          if (!exists && Number(count?.total || 0) >= 8) return json({ error: "Movie GM supports up to 8 household profiles" }, 400);
          await env.DB.prepare(`INSERT INTO movie_viewers
            (viewer_id,user_id,display_name,weight,preferred_genres_json,disliked_genres_json,preferred_keywords_json,disliked_keywords_json,preferred_runtime_min,preferred_runtime_max,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id,viewer_id) DO UPDATE SET display_name=excluded.display_name,weight=excluded.weight,
              preferred_genres_json=excluded.preferred_genres_json,disliked_genres_json=excluded.disliked_genres_json,
              preferred_keywords_json=excluded.preferred_keywords_json,disliked_keywords_json=excluded.disliked_keywords_json,
              preferred_runtime_min=excluded.preferred_runtime_min,preferred_runtime_max=excluded.preferred_runtime_max,updated_at=excluded.updated_at`)
            .bind(viewer.viewerId, identity.user_id, viewer.displayName, viewer.weight,
              JSON.stringify(viewer.preferredGenres), JSON.stringify(viewer.dislikedGenres),
              JSON.stringify(viewer.preferredKeywords), JSON.stringify(viewer.dislikedKeywords),
              viewer.runtimeMin, viewer.runtimeMax, exists?.created_at || stamp, stamp).run();
          return json({ saved: true, viewer: { viewer_id: viewer.viewerId, display_name: viewer.displayName, weight: viewer.weight,
            preferred_genres: viewer.preferredGenres, disliked_genres: viewer.dislikedGenres,
            preferred_keywords: viewer.preferredKeywords, disliked_keywords: viewer.dislikedKeywords,
            preferred_runtime_min: viewer.runtimeMin, preferred_runtime_max: viewer.runtimeMax } }, exists ? 200 : 201);
        } catch { return json({ error: "Movie GM household profile storage unavailable" }, 503); }
      }
    }
    const viewerMatch = /^\/api\/v1\/movies\/viewers\/([^/]+)$/.exec(path);
    if (viewerMatch && request.method === "DELETE") {
      try {
        const viewerId = decodeURIComponent(viewerMatch[1]);
        const result = await env.DB.prepare("DELETE FROM movie_viewers WHERE user_id=? AND viewer_id=?").bind(identity.user_id, viewerId).run();
        return result.meta?.changes ? json({ deleted: true }) : json({ error: "Viewer not found" }, 404);
      } catch { return json({ error: "Movie GM household profile deletion unavailable" }, 503); }
    }

    if (path === "/api/v1/movies/feedback") {
      if (request.method === "GET") {
        try {
          const rows = await env.DB.prepare("SELECT title,rating,watched,genres_json,created_at FROM movie_feedback WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 200").bind(identity.user_id).all();
          const preferred = new Map(), disliked = new Map();
          for (const row of rows.results || []) {
            if (!["loved", "liked", "disliked"].includes(row.rating)) continue;
            const target = row.rating === "disliked" ? disliked : preferred;
            for (const genre of JSON.parse(row.genres_json || "[]")) target.set(genre, (target.get(genre) || 0) + 1);
          }
          const top = (map) => [...map.entries()].sort((a,b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0,8).map(([genre]) => genre);
          const evidence = (rows.results || []).filter((row) => row.rating !== "fine").length;
          return json({
            evidence_count: evidence,
            preferred_genres: top(preferred),
            disliked_genres: top(disliked),
            feedback: rows.results || []
          });
        } catch { return json({ error: "Movie GM feedback unavailable" }, 503); }
      }
      if (request.method === "POST") {
        let input; try { input = await bodyObject(request); } catch { return json({ error: "Invalid request" }, 400); }
        const title = typeof input.title === "string" ? input.title.trim() : "";
        const rating = typeof input.rating === "string" ? input.rating.casefold?.() || input.rating.toLowerCase() : "";
        const genres = Array.isArray(input.genres) ? [...new Set(input.genres.filter((value) => typeof value === "string").map((value) => value.trim()).filter(Boolean))].slice(0,20) : [];
        if (!title || title.length > 300 || !["loved","liked","fine","disliked"].includes(rating)) return json({ error: "Movie feedback requires a title and valid rating" }, 400);
        if (JSON.stringify(genres).length > 2048) return json({ error: "Movie feedback genres are too large" }, 400);
        const stamp = now();
        try {
          await env.DB.prepare("INSERT INTO movie_feedback(id,user_id,title_key,title,rating,watched,genres_json,created_at) VALUES (?,?,?,?,?,?,?,?)")
            .bind(crypto.randomUUID(), identity.user_id, title.toLowerCase().replace(/\s+/g," ").trim(), title, rating, rating === "disliked" ? 0 : 1, JSON.stringify(genres), stamp).run();
          return json({ saved: true, rating, title });
        } catch { return json({ error: "Movie GM feedback storage unavailable" }, 503); }
      }
    }

    if (request.method === "POST" && path === "/api/v1/searches") {
      let input; try { input = await bodyObject(request); } catch { return json({ error: "Invalid request" }, 400); }
      if (input.module !== "family-deals") return json({ error: "Module search is not available yet" }, 400);
      let criteria; try { criteria = validateFamilyDealsCriteria(input.criteria); } catch (error) { return json({ error: error.message }, 400); }
      const id = crypto.randomUUID(), jobId = crypto.randomUUID(), stamp = now();
      const stored = { ...criteria }; delete stored.max_total_cents;
      try {
        await env.DB.batch([
          env.DB.prepare("INSERT INTO searches(id,user_id,module,criteria_json,schema_version,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)").bind(id, identity.user_id, "family-deals", JSON.stringify(stored), 1, "QUEUED", stamp, stamp),
          env.DB.prepare("INSERT INTO jobs(id,user_id,search_id,module,status,due_at,idempotency_key,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)").bind(jobId, identity.user_id, id, "family-deals", "QUEUED", stamp, `search:${id}`, stamp, stamp),
        ]);
      } catch { return json({ error: "Storage temporarily unavailable; search was not confirmed" }, 503); }
      let dispatch;
      try { dispatch = await dispatchPending(env); } catch (error) {
        console.error("Family Deals dispatch failed", error instanceof Error ? error.message : "unknown error");
        dispatch = "dispatch_error";
      }
      if (dispatch.startsWith("dispatch_") || dispatch === "not_configured") {
        const reason = dispatch === "not_configured" ? "worker_dispatch_not_configured" :
          dispatch === "dispatch_unauthorized" ? "worker_dispatch_unauthorized" :
          dispatch === "dispatch_forbidden" ? "worker_dispatch_forbidden" :
          dispatch === "dispatch_not_found" ? "worker_dispatch_not_found" :
          dispatch === "dispatch_invalid" ? "worker_dispatch_invalid" :
          dispatch === "dispatch_network" ? "worker_dispatch_network" :
          dispatch === "dispatch_db_pending" ? "worker_dispatch_db_pending" :
          dispatch === "dispatch_db_gate" ? "worker_dispatch_db_gate" :
          dispatch === "dispatch_db_gate_read" ? "worker_dispatch_db_gate_read" :
          dispatch === "dispatch_db_delay" ? "worker_dispatch_db_delay" :
          dispatch.startsWith("dispatch_http_") ? `worker_${dispatch}` : "worker_dispatch_error";
        try {
          await env.DB.batch([
            env.DB.prepare("UPDATE searches SET status='FAILED',last_outcome='ERROR',updated_at=?,completed_at=? WHERE id=? AND user_id=? AND status='QUEUED'")
              .bind(stamp, stamp, id, identity.user_id),
            env.DB.prepare("UPDATE jobs SET status='FAILED',delay_reason=?,updated_at=? WHERE id=? AND user_id=? AND status='QUEUED'")
              .bind(reason, stamp, jobId, identity.user_id),
          ]);
        } catch (error) {
          console.error("Family Deals dispatch failure could not be persisted", error instanceof Error ? error.message : "unknown error");
        }
        return json({ id, module: "family-deals", status: "FAILED", dispatch, error: reason, created_at: stamp }, 503);
      }
      return json({ id, module: "family-deals", status: "QUEUED", dispatch, created_at: stamp }, 202);
    }
    if (request.method === "GET" && path === "/api/v1/searches/latest") {
      const module = url.searchParams.get("module") || "family-deals";
      if (module !== "family-deals") return json({ error: "Search module is not available" }, 400);
      try {
        const row = await env.DB.prepare(`SELECT id,module,status,last_outcome,coverage_json,created_at,updated_at,completed_at,
          (SELECT status FROM jobs WHERE search_id=searches.id AND user_id=searches.user_id ORDER BY created_at DESC LIMIT 1) AS job_status,
          (SELECT attempt_number FROM jobs WHERE search_id=searches.id AND user_id=searches.user_id ORDER BY created_at DESC LIMIT 1) AS attempt_number,
          (SELECT due_at FROM jobs WHERE search_id=searches.id AND user_id=searches.user_id ORDER BY created_at DESC LIMIT 1) AS due_at,
          (SELECT delay_reason FROM jobs WHERE search_id=searches.id AND user_id=searches.user_id ORDER BY created_at DESC LIMIT 1) AS delay_reason
          FROM searches WHERE module=? AND user_id=? ORDER BY created_at DESC,id DESC LIMIT 1`).bind(module, identity.user_id).first();
        if (!row) return json({ error: "No Family Deals Search found" }, 404);
        return json({ ...row, coverage: row.coverage_json ? JSON.parse(row.coverage_json) : null, coverage_json: undefined });
      } catch {
        return json({ error: "Search query unavailable" }, 503);
      }
    }
    const match = /^\/api\/v1\/searches\/([0-9a-f-]{36})$/.exec(path);
    if (request.method === "GET" && match) {
      let row; try {
        row = await env.DB.prepare(`SELECT id,module,status,last_outcome,coverage_json,created_at,updated_at,completed_at,
          (SELECT status FROM jobs WHERE search_id=searches.id AND user_id=searches.user_id ORDER BY created_at DESC LIMIT 1) AS job_status,
          (SELECT attempt_number FROM jobs WHERE search_id=searches.id AND user_id=searches.user_id ORDER BY created_at DESC LIMIT 1) AS attempt_number,
          (SELECT due_at FROM jobs WHERE search_id=searches.id AND user_id=searches.user_id ORDER BY created_at DESC LIMIT 1) AS due_at,
          (SELECT delay_reason FROM jobs WHERE search_id=searches.id AND user_id=searches.user_id ORDER BY created_at DESC LIMIT 1) AS delay_reason
          FROM searches WHERE id=? AND user_id=?`).bind(match[1], identity.user_id).first();
      }
      catch { return json({ error: "Storage temporarily unavailable" }, 503); }
      if (!row) return json({ error: "Search not found" }, 404);

      // A delayed interactive Search is allowed to retry as soon as its bounded
      // execution retry is due. Do not make the user wait for the 15-minute Cron.
      if (row.status === "DELAYED" && row.due_at && Date.parse(row.due_at) <= Date.now()) {
        const stamp = now();
        try {
          await env.DB.batch([
            env.DB.prepare(`UPDATE jobs SET status='QUEUED',delay_reason=NULL,claim_id=NULL,lease_expires_at=NULL,updated_at=?
              WHERE search_id=? AND user_id=? AND status='DELAYED' AND due_at<=?`).bind(stamp, match[1], identity.user_id, stamp),
            env.DB.prepare(`UPDATE searches SET status='QUEUED',updated_at=? WHERE id=? AND user_id=? AND status='DELAYED'`)
              .bind(stamp, match[1], identity.user_id),
          ]);
          await dispatchPending(env);
          row = await env.DB.prepare(`SELECT id,module,status,last_outcome,coverage_json,created_at,updated_at,completed_at,
            (SELECT status FROM jobs WHERE search_id=searches.id AND user_id=searches.user_id ORDER BY created_at DESC LIMIT 1) AS job_status,
            (SELECT attempt_number FROM jobs WHERE search_id=searches.id AND user_id=searches.user_id ORDER BY created_at DESC LIMIT 1) AS attempt_number,
            (SELECT due_at FROM jobs WHERE search_id=searches.id AND user_id=searches.user_id ORDER BY created_at DESC LIMIT 1) AS due_at,
            (SELECT delay_reason FROM jobs WHERE search_id=searches.id AND user_id=searches.user_id ORDER BY created_at DESC LIMIT 1) AS delay_reason
            FROM searches WHERE id=? AND user_id=?`).bind(match[1], identity.user_id).first();
        } catch (error) {
          console.error("Family Deals delayed Search retry failed", error instanceof Error ? error.message : "unknown error");
        }
      }
      return json({ ...row, coverage: row.coverage_json ? JSON.parse(row.coverage_json) : null, coverage_json: undefined });
    }
    if (request.method === "POST" && path === "/api/v1/watches") {
      let input; try { input = await bodyObject(request); } catch { return json({ error: "Invalid request" }, 400); }
      if (!/^[0-9a-f-]{36}$/.test(input.search_id || "")) return json({ error: "Choose a Search to keep watching" }, 400);
      const stamp = now(), id = crypto.randomUUID();
      try {
        const source = await env.DB.prepare("SELECT module,criteria_json,schema_version,status FROM searches WHERE id=? AND user_id=?")
          .bind(input.search_id, identity.user_id).first();
        if (!source) return json({ error: "Search not found" }, 404);
        if (source.module !== "family-deals" || source.schema_version !== 1) return json({ error: "Watch module is not available" }, 400);
        if (source.status !== "COMPLETED") return json({ error: "Wait for this Search to finish before saving a Watch" }, 409);
        // Revalidate the stored versioned payload instead of trusting client fields.
        validateFamilyDealsCriteria(JSON.parse(source.criteria_json));
        const next = nextWatchCheck(new Date(stamp));
        await env.DB.batch([
          env.DB.prepare(`INSERT INTO watches(id,user_id,source_search_id,module,criteria_json,schema_version,status,next_check_at,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)`).bind(id, identity.user_id, input.search_id, source.module,
            source.criteria_json, source.schema_version, "ACTIVE", next, stamp, stamp),
          env.DB.prepare(`INSERT INTO watch_criteria_versions(watch_id,user_id,version,source_search_id,criteria_json,schema_version,created_at)
            VALUES (?,?,1,?,?,?,?)`).bind(id, identity.user_id, input.search_id, source.criteria_json, source.schema_version, stamp),
        ]);
        return json({ id, source_search_id: input.search_id, module: source.module, criteria_version: 1, status: "ACTIVE", next_check_at: next }, 201);
      } catch { return json({ error: "Watch storage unavailable" }, 503); }
    }
    if (request.method === "GET" && path === "/api/v1/watches") {
      try {
        const rows = await env.DB.prepare(`SELECT id,source_search_id,module,criteria_json,criteria_version,status,last_outcome,coverage_json,last_checked_at,next_check_at,created_at,updated_at
          FROM watches WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 100`).bind(identity.user_id).all();
        return json({ watches: (rows.results || []).map(({ criteria_json, coverage_json, ...row }) =>
          ({ ...row, criteria: JSON.parse(criteria_json), coverage: coverage_json ? JSON.parse(coverage_json) : null })) });
      } catch { return json({ error: "Watch query unavailable" }, 503); }
    }
    const watchMatch = /^\/api\/v1\/watches\/([0-9a-f-]{36})(\/check)?$/.exec(path);
    if (watchMatch) {
      const watchId = watchMatch[1];
      let watch;
      try { watch = await env.DB.prepare(`SELECT id,user_id,source_search_id,module,criteria_json,criteria_version,status,last_outcome,coverage_json,last_checked_at,next_check_at,current_fingerprint,created_at,updated_at
        FROM watches WHERE id=? AND user_id=?`).bind(watchId, identity.user_id).first(); }
      catch { return json({ error: "Watch query unavailable" }, 503); }
      if (!watch) return json({ error: "Watch not found" }, 404);
      if (request.method === "GET" && !watchMatch[2]) {
        try {
          const history = await env.DB.prepare(`SELECT event_type,outcome,fingerprint,summary,criteria_version,created_at
            FROM watch_runs WHERE watch_id=? AND user_id=? ORDER BY created_at DESC,id DESC LIMIT 50`)
            .bind(watchId, identity.user_id).all();
          const versions = await env.DB.prepare(`SELECT version,source_search_id,criteria_json,schema_version,created_at
            FROM watch_criteria_versions WHERE watch_id=? AND user_id=? ORDER BY version DESC`)
            .bind(watchId, identity.user_id).all();
          const { criteria_json, coverage_json, user_id, ...publicWatch } = watch;
          return json({ ...publicWatch, criteria: JSON.parse(criteria_json), coverage: coverage_json ? JSON.parse(coverage_json) : null,
            history: history.results || [], criteria_history: (versions.results || []).map(({ criteria_json, ...row }) => ({ ...row, criteria: JSON.parse(criteria_json) })) });
        } catch { return json({ error: "Watch history unavailable" }, 503); }
      }
      if (request.method === "POST" && watchMatch[2]) {
        if (!["ACTIVE", "FOUND"].includes(watch.status)) return json({ error: "Resume this Watch before checking" }, 409);
        const stamp = now(), jobId = crypto.randomUUID();
        try {
          await env.DB.prepare(`INSERT OR IGNORE INTO jobs(id,user_id,watch_id,module,status,due_at,idempotency_key,created_at,updated_at)
            SELECT ?,user_id,id,module,'QUEUED',?,?,?,? FROM watches
            WHERE id=? AND user_id=? AND status IN ('ACTIVE','FOUND')
              AND NOT EXISTS (SELECT 1 FROM jobs WHERE watch_id=? AND status IN ('QUEUED','CLAIMED','RUNNING','RETRYABLE','DELAYED'))`)
            .bind(jobId, stamp, `watch:${watchId}:manual:${jobId}`, stamp, stamp, watchId, identity.user_id, watchId).run();
          const inserted = await env.DB.prepare("SELECT id FROM jobs WHERE id=? AND user_id=?").bind(jobId, identity.user_id).first();
          if (!inserted) return json({ error: "A check is already queued or this Watch is not active" }, 409);
          let dispatch; try { dispatch = await dispatchPending(env); } catch { dispatch = "deferred"; }
          return json({ job_id: jobId, status: "QUEUED", dispatch }, 202);
        } catch { return json({ error: "Watch check unavailable" }, 503); }
      }
      if ((request.method === "PATCH" || request.method === "DELETE") && !watchMatch[2]) {
        let action = "stop";
        let input;
        if (request.method === "PATCH") {
          try { input = await bodyObject(request); } catch { return json({ error: "Invalid request" }, 400); }
          action = input.action;
        }
        if (action === "edit_from_search") {
          if (watch.status === "STOPPED" || !/^[0-9a-f-]{36}$/.test(input.search_id || "")) return json({ error: "Choose a completed Search" }, 400);
          try {
            const source = await env.DB.prepare("SELECT module,criteria_json,schema_version,status FROM searches WHERE id=? AND user_id=?")
              .bind(input.search_id, identity.user_id).first();
            if (!source) return json({ error: "Search not found" }, 404);
            if (source.status !== "COMPLETED" || source.module !== "family-deals" || source.schema_version !== 1) return json({ error: "Search is not ready for this Watch" }, 409);
            validateFamilyDealsCriteria(JSON.parse(source.criteria_json));
            const stamp = now(), next = nextWatchCheck(new Date(stamp)), version = watch.criteria_version + 1;
            await env.DB.batch([
              env.DB.prepare(`UPDATE watches SET source_search_id=?,module=?,criteria_json=?,schema_version=?,criteria_version=?,
                status=CASE WHEN status='PAUSED' THEN 'PAUSED' ELSE 'ACTIVE' END,
                last_outcome=NULL,last_checked_at=NULL,current_fingerprint=NULL,coverage_json=NULL,next_check_at=?,updated_at=?
                WHERE id=? AND user_id=? AND status<>'STOPPED' AND criteria_version=?
                  AND NOT EXISTS (SELECT 1 FROM jobs WHERE watch_id=? AND status IN ('QUEUED','CLAIMED','RUNNING','RETRYABLE','DELAYED'))`)
                .bind(input.search_id, source.module, source.criteria_json, source.schema_version, version,
                  next, stamp, watchId, identity.user_id, watch.criteria_version, watchId),
              env.DB.prepare(`INSERT OR IGNORE INTO watch_criteria_versions(watch_id,user_id,version,source_search_id,criteria_json,schema_version,created_at)
                SELECT id,user_id,criteria_version,source_search_id,criteria_json,schema_version,? FROM watches
                WHERE id=? AND user_id=? AND criteria_version=?`).bind(stamp, watchId, identity.user_id, version),
            ]);
            const updated = await env.DB.prepare("SELECT criteria_version,source_search_id,status FROM watches WHERE id=? AND user_id=?")
              .bind(watchId, identity.user_id).first();
            if (updated?.criteria_version !== version || updated.source_search_id !== input.search_id) return json({ error: "Finish the pending check before editing" }, 409);
            return json({ id: watchId, criteria_version: version, source_search_id: input.search_id, status: updated.status, next_check_at: next });
          } catch { return json({ error: "Watch edit unavailable" }, 503); }
        }
        const transitions = { pause: ["ACTIVE", "FOUND"], resume: ["PAUSED", "DELAYED"], keep_watching: ["FOUND"], stop: ["ACTIVE", "FOUND", "PAUSED", "DELAYED"] };
        if (!transitions[action]?.includes(watch.status)) return json({ error: "This Watch cannot make that transition" }, 409);
        const status = action === "pause" ? "PAUSED" : action === "stop" ? "STOPPED" : "ACTIVE";
        const stamp = now();
        try {
          const next = action === "resume" ? stamp :
            action === "keep_watching" ? nextWatchCheck(new Date(stamp)) : watch.next_check_at;
          const changed = await env.DB.prepare(`UPDATE watches SET status=?,next_check_at=?,updated_at=? WHERE id=? AND user_id=? AND status=? RETURNING id`)
            .bind(status, next, stamp, watchId, identity.user_id, watch.status).first();
          if (!changed) return json({ error: "Watch changed; refresh and try again" }, 409);
          if (status === "STOPPED") await env.DB.prepare(`UPDATE jobs SET status='FAILED',delay_reason='watch_stopped',updated_at=?
            WHERE watch_id=? AND user_id=? AND status IN ('QUEUED','RETRYABLE','DELAYED')`).bind(stamp, watchId, identity.user_id).run();
          return json({ id: watchId, status, next_check_at: next });
        } catch { return json({ error: "Watch update unavailable" }, 503); }
      }
    }
    if (request.method === "GET" && path === "/api/v1/results") {
      const searchId = url.searchParams.get("search_id"), watchId = url.searchParams.get("watch_id");
      const limit = Number(url.searchParams.get("limit") || 20);
      const before = url.searchParams.get("before"), beforeId = url.searchParams.get("before_id");
      if (!!searchId === !!watchId || !/^[0-9a-f-]{36}$/.test(searchId || watchId) || !Number.isInteger(limit) || limit < 1 || limit > 50 || (!!before !== !!beforeId) || (before && (!Number.isFinite(Date.parse(before)) || !/^[0-9a-f-]{36}$/.test(beforeId)))) return json({ error: "Invalid result query" }, 400);
      const column = searchId ? "search_id" : "watch_id";
      const args = [identity.user_id, searchId || watchId];
      let cursorClause = "";
      if (before) { cursorClause = " AND (created_at < ? OR (created_at = ? AND id < ?))"; args.push(before, before, beforeId); }
      try {
        const rows = await env.DB.prepare(`SELECT id,job_id,module,outcome,verification,title,summary,details_json,coverage_json,fingerprint,destination_url,observed_at,created_at FROM results
          WHERE user_id=? AND ${column}=? AND EXISTS (SELECT 1 FROM jobs j WHERE j.id=results.job_id AND j.status='COMPLETED' AND j.final_digest IS NOT NULL)
          ${cursorClause} ORDER BY created_at DESC,id DESC LIMIT ?`).bind(...args, limit + 1).all();
        const page = (rows.results || []).slice(0, limit);
        const last = page.at(-1);
        return json({ results: page.map(({ details_json, coverage_json, ...row }) => ({ ...row, details: details_json ? JSON.parse(details_json) : null, coverage: coverage_json ? JSON.parse(coverage_json) : null })), next_cursor: (rows.results || []).length > limit && last ? { before: last.created_at, before_id: last.id } : null });
      } catch { return json({ error: "Result query unavailable" }, 503); }
    }
    const resultMatch = /^\/api\/v1\/results\/([0-9a-f-]{36})$/.exec(path);
    if (request.method === "GET" && resultMatch) {
      try {
        const row = await env.DB.prepare(`SELECT id,job_id,module,outcome,verification,title,summary,details_json,coverage_json,fingerprint,destination_url,observed_at,created_at FROM results
          WHERE id=? AND user_id=? AND EXISTS (SELECT 1 FROM jobs j WHERE j.id=results.job_id AND j.status='COMPLETED' AND j.final_digest IS NOT NULL)`).bind(resultMatch[1], identity.user_id).first();
        if (!row) return json({ error: "Result not found" }, 404);
        const evidence = await env.DB.prepare("SELECT source,source_url,summary,captured_at FROM result_evidence WHERE result_id=? AND user_id=? ORDER BY id").bind(row.id, identity.user_id).all();
        const { details_json, coverage_json, ...publicRow } = row;
        return json({ ...publicRow, details: details_json ? JSON.parse(details_json) : null, coverage: coverage_json ? JSON.parse(coverage_json) : null, evidence: evidence.results || [] });
      } catch { return json({ error: "Result query unavailable" }, 503); }
    }
    if (env.ASSETS) return env.ASSETS.fetch(request);
    return json({ error: "Route not implemented" }, 404);
  },
};
