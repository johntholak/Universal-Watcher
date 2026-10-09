import asyncio
import importlib.util
import sys
import unittest
import uuid
from pathlib import Path


path = Path(__file__).parent / "family_deals_v5.py"
spec = importlib.util.spec_from_file_location("family_deals_v5_bridge", path)
bridge = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bridge
spec.loader.exec_module(bridge)

CRITERIA = {"schema_version": 1, "location": "91304", "radius_miles": 45,
            "party_size": 7, "max_total_price": 85.01,
            "cuisines": ["pizza_italian", "bbq"],
            "restaurant_type": "independent_local", "open_tonight": True}
JOB_ID = str(uuid.uuid4())


class FakePage:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.operations = []

    async def goto(self, url, **kwargs):
        self.operations.append(("goto", url))

    async def evaluate(self, script, argument=None):
        self.operations.append(("evaluate", script, argument))
        return self.snapshot if "radius_discovered:" in script else None


class FamilyDealsV5BridgeTests(unittest.TestCase):
    def test_headless_bridge_configures_exact_values_and_runs_existing_hunt(self):
        snapshot = {"radius_discovered": 0, "selected_restaurants": 0,
                    "verification": None, "error": None, "discovery_completed": True}
        page = FakePage(snapshot)
        self.assertEqual(asyncio.run(bridge.run_v5_page(page, "http://127.0.0.1:9999/", CRITERIA)), snapshot)
        configured = page.operations[1][2]
        self.assertEqual(configured["radius_miles"], 45)
        self.assertEqual(configured["max_total_price"], 85.01)
        self.assertEqual(configured["party_size"], 7)
        self.assertEqual(configured["restaurant_type"], "indie_local")
        self.assertEqual(configured["cuisines"], ["italian", "bbq"])
        self.assertIn("runHunt()", page.operations[2][1])

    def test_location_unknown_downgrades_candidate_and_preserves_evidence(self):
        snapshot = {"radius_discovered": 697, "selected_restaurants": 1,
                    "discovery_completed": True, "error": None,
                    "verification": {"status": "done", "restaurants_checked": 1,
                                     "restaurants_unavailable": 0, "restaurants_unresolved": 0,
                                     "matches": [{"name": "Example Pizza", "price": 49.99,
                                                  "capacity_verified": True, "capacity_max": 8,
                                                  "capacity_label": "4-8", "opening_status": True,
                                                  "source_url": "https://example.com/menu",
                                                  "evidence": "Family meal for 4-8 | $49.99"}]}}
        result = bridge.normalize_v5_snapshot(snapshot, CRITERIA, JOB_ID)
        self.assertEqual(result["outcome"], "PARTIAL")
        self.assertEqual(result["coverage"]["state"], "partial")
        self.assertEqual(result["radius_discovered"], 697)
        self.assertEqual(result["results"][0]["details"]["price_cents"], 4999)
        self.assertFalse(result["results"][0]["details"]["location_verified"])
        self.assertIsNone(result["results"][0]["details"]["deal_name"])
        self.assertEqual(result["results"][0]["evidence"][0]["url"], "https://example.com/menu")

    def test_failure_and_missing_coverage_never_become_no_match(self):
        failed = {"radius_discovered": 0, "selected_restaurants": 0,
                  "discovery_completed": False, "error": "Overpass blocked", "verification": None}
        self.assertEqual(bridge.normalize_v5_snapshot(failed, CRITERIA, JOB_ID)["outcome"], "UNAVAILABLE")
        incomplete = {"radius_discovered": 5, "selected_restaurants": 3,
                      "discovery_completed": True, "error": None,
                      "verification": {"status": "done", "restaurants_checked": 1,
                                       "restaurants_unavailable": 1, "restaurants_unresolved": 1, "matches": []}}
        self.assertEqual(bridge.normalize_v5_snapshot(incomplete, CRITERIA, JOB_ID)["outcome"], "PARTIAL")

    def test_progressive_snapshot_publishes_candidates_without_claiming_complete_coverage(self):
        snapshot = {"radius_discovered": 20, "selected_restaurants": 3,
                    "discovery_completed": True, "error": None,
                    "verification": {"status": "checking", "restaurants_checked": 1,
                                     "restaurants_unavailable": 0, "restaurants_unresolved": 1,
                                     "matches": [{"name": "Example Pizza", "price": 49.99,
                                                  "capacity_verified": True, "capacity_max": 8,
                                                  "capacity_label": "4-8", "opening_status": True,
                                                  "restaurantClass": "independent", "source_direct": True,
                                                  "source_url": "https://example.com/menu",
                                                  "evidence": "Family meal for 4-8 | $49.99"}]}}
        result = bridge.normalize_v5_snapshot(snapshot, CRITERIA, JOB_ID)
        self.assertEqual(result["outcome"], "PARTIAL")
        self.assertEqual(result["coverage"], {"state": "partial", "radius_discovered": 20,
                                               "discovered": 3, "checked": 1, "unavailable": 0, "unresolved": 1})
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["outcome"], "PARTIAL")
        self.assertIsNone(result["results"][0]["details"]["deal_name"])
        self.assertIn("found so far", result["summary"])

    def test_unmappable_candidate_never_becomes_no_match(self):
        snapshot = {"radius_discovered": 1, "selected_restaurants": 1,
                    "discovery_completed": True, "error": None,
                    "verification": {"status": "done", "restaurants_checked": 1,
                                     "restaurants_unavailable": 0, "restaurants_unresolved": 0,
                                     "matches": [{"name": "Example", "price": 40,
                                                  "capacity_verified": True, "evidence": ""}]}}
        result = bridge.normalize_v5_snapshot(snapshot, CRITERIA, JOB_ID)
        self.assertEqual(result["outcome"], "PARTIAL")
        self.assertEqual(result["coverage"]["state"], "partial")
        self.assertEqual(result["results"], [])


if __name__ == "__main__":
    unittest.main()
