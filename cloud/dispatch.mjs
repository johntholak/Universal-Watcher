// A fixed workflow and an atomic D1 gate keep dispatch bounded. No criteria leave D1.
const WORKFLOW_URL = "https://api.github.com/repos/johntholak/Universal-Watcher/actions/workflows/family-deals-worker.yml/dispatches";
const COOLDOWN_MS = 15 * 60 * 1000;

export async function dispatchPending(env, at = new Date()) {
  if (env.DISPATCH_ENABLED !== "true") return "not_connected";
  const limit = Number(env.DISPATCH_DAILY_LIMIT);
  if (!Number.isInteger(limit) || limit < 1 || limit > 100 || typeof env.GITHUB_DISPATCH_TOKEN !== "string" || env.GITHUB_DISPATCH_TOKEN.length < 20) return "not_configured";
  const stamp = at.toISOString();
  const day = stamp.slice(0, 10);
  const pending = await env.DB.prepare("SELECT id FROM jobs WHERE module='family-deals' AND status IN ('QUEUED','RETRYABLE') AND due_at<=? LIMIT 1").bind(stamp).first();
  if (!pending) return "idle";

  // Count the reservation before contacting GitHub. An ambiguous network failure
  // must not let retries exceed the configured free-run allowance.
  const reserved = await env.DB.prepare(`UPDATE dispatch_gate SET
      utc_day=?, runs_today=CASE WHEN utc_day=? THEN runs_today+1 ELSE 1 END,
      next_allowed_at=?, updated_at=?
    WHERE id=1 AND next_allowed_at<=? AND (utc_day<>? OR runs_today<?)
    RETURNING runs_today`).bind(day, day, new Date(at.getTime() + COOLDOWN_MS).toISOString(), stamp, stamp, day, limit).first();
  if (!reserved) return "deferred";

  try {
    const response = await fetch(WORKFLOW_URL, {
      method: "POST",
      headers: { Authorization: `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
                 Accept: "application/vnd.github+json", "Content-Type": "application/json",
                 "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "Universal-Watcher" },
      body: JSON.stringify({ ref: "main" }),
    });
    return response.status === 204 ? "signaled" : "deferred";
  } catch {
    return "deferred";
  }
}
