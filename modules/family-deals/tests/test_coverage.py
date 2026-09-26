import importlib.util
import sys
import unittest
from pathlib import Path


path = Path(__file__).resolve().parents[1] / "server.py"
spec = importlib.util.spec_from_file_location("family_deals_server_coverage", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class RestaurantCoverageTests(unittest.TestCase):
    def test_shared_source_counts_each_restaurant_and_separates_failures(self):
        restaurants = [
            {"resolvedWebsite": "https://shared.example"},
            {"resolvedWebsite": "https://shared.example"},
            {"resolvedWebsite": "https://blocked.example"},
            {"resolvedWebsite": ""},
        ]
        sources = {"https://shared.example": {"status": "checked"},
                   "https://blocked.example": {"status": "blocked"}}
        self.assertEqual(module.restaurant_coverage(restaurants, sources), {
            "restaurants_checked": 2, "restaurants_unavailable": 1,
            "restaurants_unresolved": 1,
        })


if __name__ == "__main__":
    unittest.main()
