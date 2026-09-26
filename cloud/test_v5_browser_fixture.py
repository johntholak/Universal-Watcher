"""Full V5 page fixture, runnable only where pinned Chromium is installed.

All non-loopback requests are intercepted or aborted. No provider is contacted.
"""

import asyncio
import importlib.util
import json
import sys
import unittest
from pathlib import Path

from playwright.async_api import async_playwright


root = Path(__file__).parent
for name in ("family_deals_v5", "run_family_deals_batch"):
    spec = importlib.util.spec_from_file_location(name, root / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

bridge = sys.modules["family_deals_v5"]
runner = sys.modules["run_family_deals_batch"]


class V5BrowserFixtureTests(unittest.TestCase):
    def test_full_radius_discovery_filters_and_verifier_boundary(self):
        async def exercise():
            async with async_playwright() as playwright:
                if not Path(playwright.chromium.executable_path).exists():
                    raise unittest.SkipTest("Pinned Playwright Chromium is not installed")
                with runner.local_v5_server() as base:
                    browser = await playwright.chromium.launch(headless=True)
                    try:
                        page = await browser.new_page()
                        seen = {"overpass": 0, "restaurants": None, "budget": None}

                        async def fixture(route):
                            request = route.request
                            url = request.url
                            if url.endswith("/api/interpreter"):
                                seen["overpass"] += 1
                                assert "around:72421" in (request.post_data or "") or "around%3A72421" in (request.post_data or "")
                                data = {"elements": [
                                    {"type": "node", "id": 1, "lat": 34.2, "lon": -118.6,
                                     "tags": {"name": "Example Pizza", "amenity": "restaurant", "cuisine": "pizza"}},
                                    {"type": "node", "id": 2, "lat": 34.2001, "lon": -118.6,
                                     "tags": {"name": "Example Pizza", "amenity": "restaurant", "cuisine": "pizza"}},
                                    {"type": "node", "id": 3, "lat": 34.21, "lon": -118.6,
                                     "tags": {"name": "Pizza Hut", "amenity": "restaurant", "cuisine": "pizza"}},
                                ]}
                                return await route.fulfill(json=data)
                            if "/api/verify/start" in url:
                                payload = json.loads(request.post_data)
                                seen["restaurants"] = payload["restaurants"]
                                seen["budget"] = payload["budget"]
                                return await route.fulfill(json={"job_id": "fixture"})
                            if "/api/verify/status" in url:
                                return await route.fulfill(json={
                                    "status": "done", "restaurants_checked": 1,
                                    "restaurants_unavailable": 0, "restaurants_unresolved": 0,
                                    "matches": [{"name": "Example Pizza", "price": 75,
                                                 "capacity_verified": True, "capacity_max": 7,
                                                 "capacity_label": "7", "opening_status": True,
                                                 "source_url": "https://example.com/menu",
                                                 "evidence": "A family meal for seven costs $75"}],
                                })
                            if url.startswith(base):
                                return await route.continue_()
                            return await route.abort()

                        await page.route("**/*", fixture)
                        criteria = {"schema_version": 1, "location": "34.2, -118.6",
                                    "radius_miles": 45, "party_size": 7, "max_total_price": 85.01,
                                    "cuisines": ["pizza_italian"], "restaurant_type": "independent_local",
                                    "open_tonight": True}
                        snapshot = await bridge.run_v5_page(page, base, criteria)
                        result = bridge.normalize_v5_snapshot(snapshot, criteria,
                                                              "00000000-0000-4000-8000-000000000001")
                        self.assertEqual(seen["overpass"], 1)
                        self.assertEqual(snapshot["radius_discovered"], 2)
                        self.assertEqual(snapshot["selected_restaurants"], 1)
                        self.assertEqual(len(seen["restaurants"]), 1)
                        self.assertEqual(seen["budget"], 85.01)
                        self.assertEqual(result["outcome"], "PARTIAL")
                        self.assertFalse(result["results"][0]["details"]["location_verified"])
                    finally:
                        await browser.close()

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
