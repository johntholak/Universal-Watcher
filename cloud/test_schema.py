import json
import sqlite3
import unittest
from pathlib import Path


SCHEMA = (Path(__file__).parent / "migrations" / "0001_initial.sql").read_text(encoding="utf-8")


class D1SchemaTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript(SCHEMA)
        self.db.execute("INSERT INTO users(id,created_at) VALUES (?,?)", ("u1", "2026-09-26T00:00:00Z"))

    def tearDown(self):
        self.db.close()

    def test_tables_and_due_indexes_exist(self):
        names = {row[0] for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"users", "searches", "watches", "jobs", "watch_runs", "results", "result_evidence", "provider_status", "notifications"} <= names)
        indexes = {row[0] for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        self.assertTrue({"watches_due", "jobs_due", "results_user_created", "notifications_unread"} <= indexes)

    def test_versioned_search_criteria_and_one_time_job(self):
        now = "2026-09-26T00:00:00Z"
        criteria = {"schema_version": 1, "location": "91304", "radius_miles": 2, "party_size": 7, "max_total_price": 85}
        self.db.execute("INSERT INTO searches(id,user_id,module,criteria_json,schema_version,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)", ("s1", "u1", "family-deals", json.dumps(criteria), 1, "QUEUED", now, now))
        self.db.execute("INSERT INTO jobs(id,user_id,search_id,module,status,due_at,idempotency_key,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)", ("j1", "u1", "s1", "family-deals", "QUEUED", now, "search:s1", now, now))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO jobs(id,user_id,search_id,module,status,due_at,idempotency_key,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)", ("j2", "u1", "s1", "family-deals", "QUEUED", now, "search:s1", now, now))
        self.assertEqual(json.loads(self.db.execute("SELECT criteria_json FROM searches WHERE id='s1'").fetchone()[0]), criteria)

    def test_job_must_belong_to_exactly_one_search_or_watch(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO jobs(id,user_id,module,status,due_at,idempotency_key,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)", ("j0", "u1", "family-deals", "QUEUED", "2026-09-26", "invalid", "2026-09-26", "2026-09-26"))
