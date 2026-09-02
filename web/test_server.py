import json
import threading
import unittest
from datetime import datetime, timezone
from http.client import HTTPConnection

from server import DraftWatchStore, make_handler, serialize_result
from http.server import ThreadingHTTPServer
from core.contracts import Evidence, WatchResult


class PreviewServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = DraftWatchStore()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.store))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, body=None):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        encoded = json.dumps(body).encode("utf-8") if body is not None else None
        connection.request(method, path, body=encoded, headers=headers)
        response = connection.getresponse()
        content = response.read()
        content_type = response.getheader("Content-Type", "")
        connection.close()
        parsed = json.loads(content) if content and content_type.startswith("application/json") else content
        return response.status, parsed

    def test_static_shell_and_modules_are_served(self):
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Universal Watcher", body if isinstance(body, bytes) else b"")

        status, modules = self.request("GET", "/api/modules")
        self.assertEqual(status, 200)
        self.assertEqual([module["id"] for module in modules], ["movies", "tickets", "family-deals"])

    def test_valid_draft_uses_shared_watch_contract(self):
        status, draft = self.request("POST", "/api/watches", {"module": "movies", "query": "The Odyssey"})
        self.assertEqual(status, 201)
        self.assertEqual(draft["module"], "movies")
        self.assertEqual(draft["query"], "The Odyssey")
        self.assertEqual(draft["status"], "draft")
        self.assertTrue(draft["watch_id"].startswith("draft-"))

        status, watches = self.request("GET", "/api/watches")
        self.assertEqual(status, 200)
        self.assertEqual(watches[0]["watch_id"], draft["watch_id"])

    def test_invalid_drafts_are_rejected(self):
        status, _ = self.request("POST", "/api/watches", {"module": "movies", "query": ""})
        self.assertEqual(status, 400)
        status, _ = self.request("POST", "/api/watches", {"module": "drop-watch", "query": "Anything"})
        self.assertEqual(status, 400)

    def test_lifecycle_endpoint_uses_shared_transition_rules(self):
        status, draft = self.request("POST", "/api/watches", {"module": "tickets", "query": "Example event"})
        self.assertEqual(status, 201)
        watch_id = draft["watch_id"]

        status, active = self.request("PATCH", f"/api/watches/{watch_id}", {"status": "active"})
        self.assertEqual(status, 200)
        self.assertEqual(active["status"], "active")
        status, paused = self.request("PATCH", f"/api/watches/{watch_id}", {"status": "paused"})
        self.assertEqual(status, 200)
        self.assertEqual(paused["status"], "paused")
        status, stopped = self.request("PATCH", f"/api/watches/{watch_id}", {"status": "completed"})
        self.assertEqual(status, 200)
        self.assertEqual(stopped["status"], "completed")

        status, _ = self.request("PATCH", f"/api/watches/{watch_id}", {"status": "active"})
        self.assertEqual(status, 400)

    def test_results_endpoint_is_empty_until_an_adapter_publishes_results(self):
        status, results = self.request("GET", "/api/results")
        self.assertEqual(status, 200)
        self.assertEqual(results, [])

    def test_result_serialization_preserves_evidence_and_truthful_outcome(self):
        result = WatchResult(
            result_id="result-1",
            watch_id="watch-1",
            module="movies",
            title="The Odyssey · CityWalk",
            outcome="unavailable",
            verification="unverified",
            coverage="partial",
            evidence=(Evidence(source="AMC", kind="diagnostic", summary="Showtime discovery unavailable"),),
            reason="The source could not be checked.",
            observed_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
        )
        serialized = serialize_result(result)
        self.assertEqual(serialized["outcome"], "unavailable")
        self.assertEqual(serialized["evidence"][0]["summary"], "Showtime discovery unavailable")
        self.assertEqual(serialized["reason"], "The source could not be checked.")


if __name__ == "__main__":
    unittest.main()
