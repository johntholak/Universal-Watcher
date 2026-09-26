-- D1 / SQLite schema. User-owned records are scoped by user_id.
PRAGMA foreign_keys = ON;

CREATE TABLE users (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  auth_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE searches (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  module TEXT NOT NULL CHECK (module IN ('family-deals', 'movies')),
  criteria_json TEXT NOT NULL CHECK (json_valid(criteria_json)),
  schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
  status TEXT NOT NULL CHECK (status IN ('QUEUED','RUNNING','COMPLETED','DELAYED','FAILED')),
  last_outcome TEXT CHECK (last_outcome IN ('MATCH','NO_MATCH','PARTIAL','UNAVAILABLE','ERROR')),
  coverage_json TEXT CHECK (coverage_json IS NULL OR json_valid(coverage_json)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT
);
CREATE INDEX searches_user_created ON searches(user_id, created_at DESC);
CREATE INDEX searches_user_status ON searches(user_id, status);

CREATE TABLE watches (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  source_search_id TEXT REFERENCES searches(id),
  module TEXT NOT NULL CHECK (module IN ('family-deals', 'movies')),
  criteria_json TEXT NOT NULL CHECK (json_valid(criteria_json)),
  schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
  status TEXT NOT NULL CHECK (status IN ('ACTIVE','FOUND','PAUSED','STOPPED','EXPIRED','DELAYED')),
  last_outcome TEXT CHECK (last_outcome IN ('MATCH','NO_MATCH','PARTIAL','UNAVAILABLE','ERROR')),
  last_checked_at TEXT,
  next_check_at TEXT,
  current_fingerprint TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX watches_user_status ON watches(user_id, status, created_at DESC);
CREATE INDEX watches_due ON watches(status, next_check_at) WHERE status IN ('ACTIVE','FOUND','DELAYED');

CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  search_id TEXT REFERENCES searches(id),
  watch_id TEXT REFERENCES watches(id),
  module TEXT NOT NULL CHECK (module IN ('family-deals', 'movies')),
  status TEXT NOT NULL CHECK (status IN ('QUEUED','CLAIMED','RUNNING','COMPLETED','RETRYABLE','DELAYED','FAILED')),
  due_at TEXT NOT NULL,
  claim_id TEXT,
  claimed_at TEXT,
  lease_expires_at TEXT,
  attempt_number INTEGER NOT NULL DEFAULT 0 CHECK (attempt_number >= 0),
  idempotency_key TEXT NOT NULL UNIQUE,
  delay_reason TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK ((search_id IS NOT NULL) <> (watch_id IS NOT NULL))
);
CREATE INDEX jobs_due ON jobs(status, due_at, lease_expires_at);
CREATE INDEX jobs_user_status ON jobs(user_id, status);
CREATE INDEX jobs_watch ON jobs(watch_id, created_at DESC);

CREATE TABLE watch_runs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  watch_id TEXT NOT NULL REFERENCES watches(id),
  job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),
  event_type TEXT NOT NULL,
  outcome TEXT CHECK (outcome IN ('MATCH','NO_MATCH','PARTIAL','UNAVAILABLE','ERROR')),
  fingerprint TEXT,
  summary TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX watch_runs_history ON watch_runs(user_id, watch_id, created_at DESC);

CREATE TABLE results (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  job_id TEXT NOT NULL REFERENCES jobs(id),
  search_id TEXT REFERENCES searches(id),
  watch_id TEXT REFERENCES watches(id),
  module TEXT NOT NULL CHECK (module IN ('family-deals', 'movies')),
  outcome TEXT NOT NULL CHECK (outcome IN ('MATCH','NO_MATCH','PARTIAL','UNAVAILABLE','ERROR')),
  verification TEXT NOT NULL CHECK (verification IN ('VERIFIED','PARTIALLY_VERIFIED','UNABLE_TO_VERIFY')),
  title TEXT NOT NULL,
  summary TEXT,
  details_json TEXT CHECK (details_json IS NULL OR json_valid(details_json)),
  coverage_json TEXT CHECK (coverage_json IS NULL OR json_valid(coverage_json)),
  fingerprint TEXT,
  destination_url TEXT,
  observed_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (job_id, id)
);
CREATE INDEX results_user_created ON results(user_id, created_at DESC);
CREATE INDEX results_search ON results(user_id, search_id, created_at DESC);
CREATE INDEX results_watch ON results(user_id, watch_id, created_at DESC);

CREATE TABLE result_evidence (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  result_id TEXT NOT NULL REFERENCES results(id),
  source TEXT NOT NULL,
  source_url TEXT,
  summary TEXT NOT NULL,
  captured_at TEXT NOT NULL
);
CREATE INDEX evidence_result ON result_evidence(user_id, result_id);

CREATE TABLE provider_status (
  provider TEXT PRIMARY KEY,
  state TEXT NOT NULL CHECK (state IN ('HEALTHY','DEGRADED','RATE_LIMITED','BLOCKED','UNAVAILABLE')),
  next_probe_at TEXT,
  failure_count INTEGER NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
  compact_reason TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE notifications (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  watch_id TEXT NOT NULL REFERENCES watches(id),
  result_id TEXT REFERENCES results(id),
  event_key TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('NEW','READ')),
  created_at TEXT NOT NULL,
  read_at TEXT,
  UNIQUE (user_id, event_key, fingerprint)
);
CREATE INDEX notifications_unread ON notifications(user_id, state, created_at DESC);
