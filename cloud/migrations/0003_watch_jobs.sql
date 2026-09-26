-- Prevent a Watch from having two pending/running checks at once.
ALTER TABLE watches ADD COLUMN coverage_json TEXT CHECK (coverage_json IS NULL OR json_valid(coverage_json));
CREATE UNIQUE INDEX watch_one_active_job ON jobs(watch_id)
  WHERE watch_id IS NOT NULL AND status IN ('QUEUED','CLAIMED','RUNNING','RETRYABLE','DELAYED');
