import json
import threading
import unittest
from http.client import HTTPConnection

from server import DraftWatchStore, make_handler
from http.server import ThreadingHTTPServer


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


if __name__ == "__main__":
    unittest.main()
