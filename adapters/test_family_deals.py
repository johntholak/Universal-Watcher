import unittest

from family_deals import FamilyDealsAdapter, normalize_family_deals_job
from core.contracts import WatchDefinition


def make_watch():
    return WatchDefinition("watch-1", "family-deals", "Family dinner deals")


class FamilyDealsAdapterTests(unittest.TestCase):
    def test_verified_match_keeps_source_evidence_and_destination(self):
        results = normalize_family_deals_job(
            {
                "id": "job-1",
                "status": "done",
                "total": 1,
                "processed": 1,
                "sources_total": 1,
                "sources_checked": 1,
                "matches": [
                    {
                        "name": "Example Kitchen",
                        "price": 38,
                        "capacity_label": "6",
                        "evidence": "Family meal includes entree, sides, and dessert.",
                        "source_url": "https://example.test/menu",
                    }
                ],
            },
            make_watch(),
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].outcome, "match")
        self.assertEqual(results[0].verification, "verified")
        self.assertEqual(results[0].coverage, "complete")
        self.assertEqual(results[0].evidence[0].url, "https://example.test/menu")
        self.assertEqual(results[0].destination_url, "https://example.test/menu")

    def test_uncertain_hours_are_unavailable_not_a_verified_match(self):
        results = normalize_family_deals_job(
            {
                "id": "job-2",
                "status": "done",
                "total": 1,
                "processed": 1,
                "sources_total": 1,
                "sources_checked": 1,
                "needs_hours": [{"name": "Example Kitchen", "price": 38, "capacity_label": "6"}],
            },
            make_watch(),
        )
        self.assertEqual(results[0].outcome, "unavailable")
        self.assertEqual(results[0].verification, "unverified")
        self.assertIn("dinner availability", results[0].reason)

    def test_uncertain_capacity_is_unavailable(self):
        results = normalize_family_deals_job(
            {
                "id": "job-3",
                "status": "done",
                "total": 1,
                "processed": 1,
                "sources_total": 1,
                "sources_checked": 1,
                "needs_capacity": [{"name": "Example Kitchen", "price": 38}],
            },
            make_watch(),
        )
        self.assertEqual(results[0].outcome, "unavailable")
        self.assertIn("serving capacity", results[0].reason)

    def test_partial_no_match_is_labeled_unverified_with_coverage(self):
        results = normalize_family_deals_job(
            {
                "id": "job-4",
                "status": "done",
                "total": 10,
                "processed": 10,
                "sources_total": 5,
                "sources_checked": 5,
                "unresolved": 3,
                "blocked": 1,
                "message": "Strict verification complete: 0 fully verified matches",
            },
            make_watch(),
        )
        self.assertEqual(results[0].outcome, "no_match")
        self.assertEqual(results[0].verification, "unverified")
        self.assertEqual(results[0].coverage, "partial")
        self.assertIn("3 unresolved", results[0].evidence[0].summary)

    def test_in_progress_job_is_unavailable(self):
        results = normalize_family_deals_job(
            {"id": "job-5", "status": "checking", "message": "Checking official sources"},
            make_watch(),
        )
        self.assertEqual(results[0].outcome, "unavailable")
        self.assertEqual(results[0].coverage, "unknown")

    def test_adapter_uses_injected_provider_at_run_boundary(self):
        adapter = FamilyDealsAdapter(
            lambda watch: {
                "id": watch.watch_id,
                "status": "done",
                "total": 0,
                "processed": 0,
                "sources_total": 0,
                "sources_checked": 0,
                "message": "No matching family meal",
            }
        )
        results = list(adapter.run_once(make_watch()))
        self.assertEqual(adapter.module_name, "family-deals")
        self.assertEqual(results[0].module, "family-deals")
        self.assertEqual(results[0].outcome, "no_match")


if __name__ == "__main__":
    unittest.main()
