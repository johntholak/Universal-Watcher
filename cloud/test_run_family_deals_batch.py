import asyncio
import importlib.util
import json
import sys
import unittest
import uuid
from pathlib import Path
from urllib.request import urlopen


root = Path(__file__).parent
for name in ("family_deals_v5", "run_family_deals_batch"):
    path = root / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

runner = sys.modules["run_family_deals_batch"]


class FakePage:
    async def goto(self, _url, **_kwargs):
        pass

    async def evaluate(self, script, _argument=None):
        if "radius_discovered:" in script:
            return {"radius_discovered": 4, "selected_restaurants": 1,
                    "discovery_completed": True, "error": None,
                    "verification": {"status": "done", "restaurants_checked": 1,
                                     "restaurants_unavailable": 0, "restaurants_unresolved": 0,
                                     "matches": [{"name": "Example", "price": 45,
                                                  "capacity_verified": True, "capacity_max": 7,
                                                  "capacity_label": "7", "opening_status": True,
                                                  "source_url": "https://example.com/menu",
                                                  "evidence": "Family meal for seven $45"}]}}


class ProgressiveFakePage:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)

    async def goto(self, _url, **_kwargs):
        pass

    async def evaluate(self, script, _argument=None):
        if "radius_discovered:" in script:
            return self.snapshots.pop(0)
        return True


class FailingPage(FakePage):
    async def goto(self, _url, **_kwargs):
        raise RuntimeError("Browser execution failed")


class FakeAPI:
    def __init__(self):
        self.calls = []

    def post(self, path, payload):
        self.calls.append((path, payload))
        return {"accepted": len(payload.get("items", []))}


class FamilyBatchRunnerTests(unittest.TestCase):
    def test_local_server_health_without_browser_or_provider(self):
        with runner.local_v5_server() as base:
            with urlopen(base + "api/health", timeout=2) as response:
                self.assertTrue(json.load(response)["ok"])

    def test_job_uploads_conservative_result_then_finalizes(self):
        api = FakeAPI()
        job = {"id": str(uuid.uuid4()), "claim_id": str(uuid.uuid4()),
               "criteria": {"schema_version": 1, "location": "91304", "radius_miles": 2,
                            "party_size": 7, "max_total_price": 50, "cuisines": [],
                            "restaurant_type": "any", "open_tonight": True}}
        response = asyncio.run(runner.execute_job(api, FakePage(), "http://127.0.0.1:9999/", job))
        self.assertEqual(response["outcome"], "PARTIAL")
        self.assertEqual(len(api.calls), 2)
        self.assertTrue(api.calls[0][0].endswith("/results"))
        self.assertFalse(api.calls[0][1]["items"][0]["details"]["location_verified"])
        self.assertEqual(api.calls[1][1]["outcome"], "PARTIAL")

    def test_progressive_candidates_upload_once_before_finalization(self):
        criteria = {"schema_version": 1, "location": "91304", "radius_miles": 2,
                    "party_size": 7, "max_total_price": 50, "cuisines": [],
                    "restaurant_type": "any", "open_tonight": True}
        first = {"name": "First Pizza", "price": 45, "capacity_verified": True,
                 "capacity_max": 7, "capacity_label": "7", "opening_status": True,
                 "restaurantClass": "independent", "source_direct": True,
                 "source_url": "https://example.com/first",
                 "evidence": "Family meal for seven $45"}
        second = {"name": "Second Pizza", "price": 40, "capacity_verified": True,
                  "capacity_max": 7, "capacity_label": "7", "opening_status": True,
                  "restaurantClass": "independent", "source_direct": True,
                  "source_url": "https://example.com/second",
                  "evidence": "Family meal for seven $40"}
        active = {"radius_discovered": 2, "selected_restaurants": 2,
                  "discovery_completed": True, "hunt_finished": False, "error": None,
                  "verification": {"status": "checking", "restaurants_checked": 1,
                                   "restaurants_unavailable": 0, "restaurants_unresolved": 0,
                                   "sources_checked": 1, "matches": [first]}}
        final = {"radius_discovered": 2, "selected_restaurants": 2,
                 "discovery_completed": True, "hunt_finished": True, "error": None,
                 "verification": {"status": "done", "restaurants_checked": 2,
                                  "restaurants_unavailable": 0, "restaurants_unresolved": 0,
                                  "sources_checked": 2, "matches": [first, second]}}
        api = FakeAPI()
        job = {"id": str(uuid.uuid4()), "claim_id": str(uuid.uuid4()), "criteria": criteria}
        response = asyncio.run(runner.execute_job(
            api, ProgressiveFakePage([active, final]), "http://127.0.0.1:9999/", job))
        self.assertEqual(response["candidate_count"], 2)
        self.assertEqual(len(api.calls), 3)
        self.assertEqual([x["title"] for x in api.calls[0][1]["items"]], ["Family meal offer at First Pizza"])
        self.assertEqual([x["title"] for x in api.calls[1][1]["items"]], ["Family meal offer at Second Pizza"])
        self.assertTrue(api.calls[2][0].endswith("/complete"))

    def test_execution_failure_requests_bounded_retry_without_false_result(self):
        api = FakeAPI()
        job = {"id": str(uuid.uuid4()), "claim_id": str(uuid.uuid4()),
               "criteria": {"schema_version": 1, "location": "91304", "radius_miles": 2,
                            "party_size": 7, "max_total_price": 50, "cuisines": [],
                            "restaurant_type": "any", "open_tonight": True}}
        response = asyncio.run(runner.execute_job(api, FailingPage(), "http://127.0.0.1:9999/", job))
        self.assertEqual(response["outcome"], "ERROR")
        self.assertEqual(len(api.calls), 1)
        self.assertTrue(api.calls[0][0].endswith("/failure"))
        self.assertEqual(api.calls[0][1]["category"], "execution")


if __name__ == "__main__":
    unittest.main()
