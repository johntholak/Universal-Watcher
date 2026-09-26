import { validateFamilyDealsCriteria } from "./criteria.mjs";

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
async function bodyObject(request) {
  const length = Number(request.headers.get("Content-Length") || 0);
  if (length > MAX_BODY_BYTES) throw new Error("Request is too large");
  const body = await request.text();
  if (new TextEncoder().encode(body).length > MAX_BODY_BYTES) throw new Error("Request is too large");
  const object = JSON.parse(body);
  if (!object || typeof object !== "object" || Array.isArray(object)) throw new Error("Expected a JSON object");
  return object;
}

export default {
  async fetch(request, env) {
    if (!requireConfig(env)) return json({ error: "Service is not configured" }, 503);
    const url = new URL(request.url);
    const path = url.pathname;
    if (!path.startsWith("/api/v1/")) return json({ error: "Not found" }, 404);
    if (request.method === "GET" && path === "/api/v1/system/status") return json({ state: "preview", execution: "not_connected" });

    if (request.method === "POST" && path === "/api/v1/session") {
      if (!sameOrigin(request)) return json({ error: "Invalid origin" }, 403);
      let input; try { input = await bodyObject(request); } catch { return json({ error: "Invalid request" }, 400); }
      if (typeof input.access_secret !== "string" || !equal(encode(await hmac(env.ACCESS_SECRET, input.access_secret)), encode(await hmac(env.ACCESS_SECRET, env.ACCESS_SECRET)))) return json({ error: "Access denied" }, 401);
      const expires = Date.now() + SESSION_SECONDS * 1000;
      const value = encode(new TextEncoder().encode(JSON.stringify({ user_id: "private-beta", exp: expires, nonce: crypto.randomUUID() })));
      const token = `${value}.${encode(await hmac(env.SESSION_KEY, value))}`;
      const stamp = now();
      try { await env.DB.prepare("INSERT OR IGNORE INTO users(id,created_at) VALUES (?,?)").bind("private-beta", stamp).run(); }
      catch { return json({ error: "Storage temporarily unavailable" }, 503); }
      return json({ authenticated: true, csrf_token: await csrf(env, token) }, 200, { "Set-Cookie": `${COOKIE}=${token}; Path=/; Max-Age=${SESSION_SECONDS}; HttpOnly; Secure; SameSite=Strict` });
    }

    if (path.startsWith("/api/v1/internal/")) {
      if (!(await workerAuthorized(request, env))) return json({ error: "Worker authentication required" }, 401);
      if (request.method === "POST" && path === "/api/v1/internal/jobs/claim") {
        let input; try { input = await bodyObject(request); } catch { return json({ error: "Invalid request" }, 400); }
        const limit = input.limit ?? 10;
        if (!Number.isInteger(limit) || limit < 1 || limit > 10) return json({ error: "Batch limit must be 1 through 10" }, 400);
        const stamp = now(), expires = new Date(Date.now() + 5 * 60 * 1000).toISOString(), claimId = crypto.randomUUID();
        try {
          const claimed = await env.DB.prepare(`UPDATE jobs SET status='CLAIMED', claim_id=?, claimed_at=?, lease_expires_at=?, attempt_number=attempt_number+1, updated_at=?
            WHERE id IN (SELECT id FROM jobs WHERE ((status IN ('QUEUED','RETRYABLE') AND due_at<=?) OR (status IN ('CLAIMED','RUNNING') AND lease_expires_at<?))
            ORDER BY due_at,id LIMIT ?) RETURNING id,user_id,search_id,watch_id,module,claim_id,attempt_number,lease_expires_at`).bind(claimId, stamp, expires, stamp, stamp, stamp, limit).all();
          const jobs = [];
          for (const row of claimed.results || []) {
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
      return json({ error: "Internal route not implemented" }, 404);
    }

    const identity = await session(request, env);
    if (!identity) return json({ error: "Authentication required" }, 401);
    if (request.method === "GET" && path === "/api/v1/session") return json({ authenticated: true, csrf_token: await csrf(env, identity.token) });
    if (request.method !== "GET" && (!sameOrigin(request) || !equal(request.headers.get("X-CSRF-Token") || "", await csrf(env, identity.token)))) return json({ error: "Invalid request token or origin" }, 403);

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
      return json({ id, module: "family-deals", status: "QUEUED", dispatch: "not_connected", created_at: stamp }, 202);
    }
    const match = /^\/api\/v1\/searches\/([0-9a-f-]{36})$/.exec(path);
    if (request.method === "GET" && match) {
      let row; try { row = await env.DB.prepare("SELECT id,module,status,last_outcome,coverage_json,created_at,updated_at,completed_at FROM searches WHERE id=? AND user_id=?").bind(match[1], identity.user_id).first(); }
      catch { return json({ error: "Storage temporarily unavailable" }, 503); }
      if (!row) return json({ error: "Search not found" }, 404);
      return json({ ...row, coverage: row.coverage_json ? JSON.parse(row.coverage_json) : null, coverage_json: undefined });
    }
    return json({ error: "Route not implemented" }, 404);
  },
};
