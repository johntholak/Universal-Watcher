-- Apply after 0001. One row serializes dispatch and caps daily reservations.
CREATE TABLE dispatch_gate (
  id INTEGER PRIMARY KEY CHECK (id=1),
  utc_day TEXT NOT NULL,
  runs_today INTEGER NOT NULL DEFAULT 0 CHECK (runs_today >= 0),
  next_allowed_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
INSERT INTO dispatch_gate(id,utc_day,runs_today,next_allowed_at,updated_at)
VALUES (1,'',0,'1970-01-01T00:00:00.000Z','1970-01-01T00:00:00.000Z');
