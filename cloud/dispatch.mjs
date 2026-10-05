// A fixed workflow and an atomic D1 gate keep dispatch bounded. No criteria leave D1.
const WORKFLOW_URL = "https://api.github.com/repos/johntholak/Universal-Watcher/actions/workflows/family-deals-worker.yml/dispatches";
const COOLDOWN_MS = 60 * 1000;

export async function expireExhaustedJobs(env, stamp = new Date().toISOString()) {
  const expired = await env.DB.prepare(`SELECT id,user_id,search_id,watch_id FROM jobs
    WHERE module='family-deals' AND status IN ('CLAIMED','RUNNING')
      AND attempt_number>=3 AND lease_expires_at<? ORDER BY lease_expires_at,id LIMIT 10`).bind(stamp).all();
  for (const job of expired.results || []) {
    const statements = [env.DB.prepare(`UPDATE jobs SET status='FAILED',delay_reason='attempts_exhausted',
      claim_id=NULL,lease_expires_at=NULL,updated_at=? WHERE id=? AND status IN ('CLAIMED','RUNNING')
      AND attempt_number>=3 AND lease_expires_at<?`).bind(stamp, job.id, stamp)];
    if (job.search_id) statements.push(env.DB.prepare(`UPDATE searches SET status='FAILED',last_outcome='ERROR',updated_at=?
      WHERE id=? AND user_id=? AND EXISTS (SELECT 1 FROM jobs WHERE id=? AND status='FAILED' AND delay_reason='attempts_exhausted')`)
      .bind(stamp, job.search_id, job.user_id, job.id));
    if (job.watch_id) {
      statements.push(env.DB.prepare(`UPDATE watches SET status=CASE WHEN status IN ('PAUSED','STOPPED') THEN status ELSE 'PAUSED' END,
        last_outcome='ERROR',last_checked_at=?,updated_at=? WHERE id=? AND user_id=?
        AND EXISTS (SELECT 1 FROM jobs WHERE id=? AND status='FAILED' AND delay_reason='attempts_exhausted')`)
        .bind(stamp, stamp, job.watch_id, job.user_id, job.id));
      statements.push(env.DB.prepare(`INSERT OR IGNORE INTO watch_runs(id,user_id,watch_id,job_id,event_type,outcome,summary,criteria_version,created_at)
        SELECT ?,user_id,id,?,'EXECUTION_FAILED','ERROR','Worker stopped before completion after three attempts.',criteria_version,?
        FROM watches WHERE id=? AND user_id=? AND EXISTS (SELECT 1 FROM jobs WHERE id=? AND status='FAILED' AND delay_reason='attempts_exhausted')`)
        .bind(crypto.randomUUID(), job.id, stamp, job.watch_id, job.user_id, job.id));
    }
    await env.DB.batch(statements);
  }
  return (expired.results || []).length;
}

export async function restoreFreeCapacity(env, at = new Date()) {
  if (env.DISPATCH_ENABLED !== "true") return;
  const stamp = at.toISOString();
  await env.DB.batch([
    env.DB.prepare(`UPDATE jobs SET status='QUEUED',delay_reason=NULL,updated_at=?
      WHERE status='DELAYED' AND delay_reason='free_capacity'
        AND (watch_id IS NULL OR EXISTS (SELECT 1 FROM watches w WHERE w.id=watch_id
          AND w.status IN ('ACTIVE','FOUND','DELAYED')))`)
      .bind(stamp),
    env.DB.prepare(`UPDATE searches SET status='QUEUED',updated_at=? WHERE status='DELAYED'
      AND EXISTS (SELECT 1 FROM jobs j WHERE j.search_id=searches.id AND j.status='QUEUED')`).bind(stamp),
    env.DB.prepare(`UPDATE watches SET status='ACTIVE',updated_at=? WHERE status='DELAYED'
      AND EXISTS (SELECT 1 FROM jobs j WHERE j.watch_id=watches.id AND j.status='QUEUED')`).bind(stamp),
  ]);
}

async function delayForFreeCapacity(env, at) {
  const stamp = at.toISOString();
  const reset = new Date(Date.UTC(at.getUTCFullYear(), at.getUTCMonth(), at.getUTCDate() + 1)).toISOString();
  await env.DB.batch([
    env.DB.prepare(`UPDATE jobs SET status='DELAYED',due_at=?,delay_reason='free_capacity',
        claim_id=NULL,lease_expires_at=NULL,updated_at=? WHERE module='family-deals'
      AND ((status IN ('QUEUED','RETRYABLE') AND due_at<=?)
        OR (status IN ('CLAIMED','RUNNING') AND lease_expires_at<?))
      AND (watch_id IS NULL OR EXISTS (SELECT 1 FROM watches w WHERE w.id=watch_id
        AND w.status IN ('ACTIVE','FOUND')))`)
      .bind(reset, stamp, stamp, stamp),
    env.DB.prepare(`UPDATE searches SET status='DELAYED',updated_at=? WHERE status='QUEUED'
      AND EXISTS (SELECT 1 FROM jobs j WHERE j.search_id=searches.id AND j.status='DELAYED'
        AND j.delay_reason='free_capacity')`).bind(stamp),
    env.DB.prepare(`UPDATE watches SET status='DELAYED',updated_at=? WHERE status IN ('ACTIVE','FOUND')
      AND EXISTS (SELECT 1 FROM jobs j WHERE j.watch_id=watches.id AND j.status='DELAYED'
        AND j.delay_reason='free_capacity')`).bind(stamp),
  ]);
}

export async function dispatchPending(env, at = new Date()) {
  if (env.DISPATCH_ENABLED !== "true") return "not_connected";
  const limit = Number(env.DISPATCH_DAILY_LIMIT);
  if (!Number.isInteger(limit) || limit < 1 || limit > 100 || typeof env.GITHUB_DISPATCH_TOKEN !== "string" || env.GITHUB_DISPATCH_TOKEN.length < 20) return "not_configured";
  const stamp = at.toISOString();
  const day = stamp.slice(0, 10);
  const pending = await env.DB.prepare(`SELECT j.id FROM jobs j LEFT JOIN watches w ON w.id=j.watch_id
    WHERE j.module='family-deals' AND j.attempt_number<3 AND ((j.status IN ('QUEUED','RETRYABLE') AND j.due_at<=?)
      OR (j.status IN ('CLAIMED','RUNNING') AND j.lease_expires_at<?))
      AND (j.watch_id IS NULL OR w.status IN ('ACTIVE','FOUND')
        OR (w.status='DELAYED' AND j.status IN ('RETRYABLE','CLAIMED','RUNNING'))) LIMIT 1`).bind(stamp, stamp).first();
  if (!pending) return "idle";

  // Count the reservation before contacting GitHub. An ambiguous network failure
  // must not let retries exceed the configured free-run allowance.
  const reserved = await env.DB.prepare(`UPDATE dispatch_gate SET
      utc_day=?, runs_today=CASE WHEN utc_day=? THEN runs_today+1 ELSE 1 END,
      next_allowed_at=?, updated_at=?
    WHERE id=1 AND next_allowed_at<=? AND (utc_day<>? OR runs_today<?)
    RETURNING runs_today`).bind(day, day, new Date(at.getTime() + COOLDOWN_MS).toISOString(), stamp, stamp, day, limit).first();
  if (!reserved) {
    const gate = await env.DB.prepare("SELECT utc_day,runs_today FROM dispatch_gate WHERE id=1").bind().first();
    if (gate?.utc_day === day && gate.runs_today >= limit) {
      await delayForFreeCapacity(env, at);
      return "free_capacity";
    }
    return "deferred";
  }

  try {
    const response = await fetch(WORKFLOW_URL, {
      method: "POST",
      headers: { Authorization: `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
                 Accept: "application/vnd.github+json", "Content-Type": "application/json",
                 "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "Universal-Watcher" },
      body: JSON.stringify({ ref: "main" }),
    });
    if (response.status === 200 || response.status === 204) return "signaled";
    const detail = await response.text().catch(() => "");
    console.error("GitHub workflow dispatch rejected", response.status, detail.slice(0, 300));
    return "dispatch_error";
  } catch (error) {
    console.error("GitHub workflow dispatch failed", error instanceof Error ? error.message : "unknown error");
    return "dispatch_error";
  }
}
