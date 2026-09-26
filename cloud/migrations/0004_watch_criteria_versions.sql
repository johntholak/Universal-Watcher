-- Preserve which exact criteria produced each Watch run across edits.
ALTER TABLE watches ADD COLUMN criteria_version INTEGER NOT NULL DEFAULT 1 CHECK (criteria_version >= 1);
ALTER TABLE watch_runs ADD COLUMN criteria_version INTEGER NOT NULL DEFAULT 1 CHECK (criteria_version >= 1);

CREATE TABLE watch_criteria_versions (
  watch_id TEXT NOT NULL REFERENCES watches(id),
  user_id TEXT NOT NULL REFERENCES users(id),
  version INTEGER NOT NULL CHECK (version >= 1),
  source_search_id TEXT NOT NULL REFERENCES searches(id),
  criteria_json TEXT NOT NULL CHECK (json_valid(criteria_json)),
  schema_version INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (watch_id,version)
);
CREATE INDEX watch_criteria_user ON watch_criteria_versions(user_id,watch_id,version);
INSERT INTO watch_criteria_versions(watch_id,user_id,version,source_search_id,criteria_json,schema_version,created_at)
SELECT id,user_id,1,source_search_id,criteria_json,schema_version,created_at FROM watches;
