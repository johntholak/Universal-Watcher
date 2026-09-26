// A Watch keeps the exact versioned Search criteria. Fixed 24-hour cadence
// bounds free-tier usage; Cron only queues due work, never performs a scan.
export const WATCH_INTERVAL_MS = 24 * 60 * 60 * 1000;
export const nextWatchCheck = (date = new Date()) => new Date(date.getTime() + WATCH_INTERVAL_MS).toISOString();

export async function queueDueWatches(env, stamp = new Date().toISOString()) {
  const due = await env.DB.prepare(`SELECT w.id,w.user_id,w.module,w.next_check_at FROM watches w
    WHERE w.module='family-deals' AND w.status IN ('ACTIVE','FOUND') AND w.next_check_at<=?
      AND NOT EXISTS (SELECT 1 FROM jobs j WHERE j.watch_id=w.id
        AND j.status IN ('QUEUED','CLAIMED','RUNNING','RETRYABLE','DELAYED'))
    ORDER BY w.next_check_at,w.id LIMIT 10`).bind(stamp).all();
  for (const watch of due.results || []) {
    // Both the partial unique index and the due-time key prevent duplicate
    // checks when two Cron invocations overlap.
    await env.DB.prepare(`INSERT OR IGNORE INTO jobs
      (id,user_id,watch_id,module,status,due_at,idempotency_key,created_at,updated_at)
      SELECT ?,user_id,id,module,'QUEUED',?, ?,?,? FROM watches
      WHERE id=? AND user_id=? AND status IN ('ACTIVE','FOUND') AND next_check_at=?`)
      .bind(crypto.randomUUID(), stamp, `watch:${watch.id}:${watch.next_check_at}`,
            stamp, stamp, watch.id, watch.user_id, watch.next_check_at).run();
  }
  return (due.results || []).length;
}
