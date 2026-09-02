import unittest
from datetime import datetime, timezone

from contracts import Evidence, WatchDefinition, WatchResult


class ContractTests(unittest.TestCase):
    def test_watch_definition_validates_and_changes_status(self):
        created = datetime(2026, 9, 2, tzinfo=timezone.utc)
        watch = WatchDefinition(
            watch_id="watch-1",
            module="movies",
            query="The Odyssey",
            criteria={"format": "IMAX 70MM"},
            created_at=created,
        )
        self.assertEqual(watch.status, "draft")
        self.assertEqual(watch.with_status("active").status, "active")
        self.assertEqual(watch.transition_to("active").status, "active")
        self.assertEqual(watch.created_at, created)

        with self.assertRaises(ValueError):
            watch.transition_to("paused")

    def test_watch_lifecycle_rejects_invalid_backwards_moves(self):
        watch = WatchDefinition("watch-1", "movies", "The Odyssey").transition_to("active")
        paused = watch.transition_to("paused")
        self.assertEqual(paused.transition_to("active").status, "active")
        with self.assertRaises(ValueError):
            paused.transition_to("draft")
        with self.assertRaises(ValueError):
            watch.transition_to("draft")

    def test_watch_definition_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            WatchDefinition("", "movies", "The Odyssey")
        with self.assertRaises(ValueError):
            WatchDefinition("watch-1", "movies", "The Odyssey", status="finished")
        with self.assertRaises(TypeError):
            WatchDefinition("watch-1", "movies", "The Odyssey", criteria=["not", "a", "mapping"])

    def test_result_keeps_unavailable_distinct_from_no_match(self):
        evidence = Evidence("AMC", "seat-inventory", "Inventory was captured and checked.")
        no_match = WatchResult("result-1", "watch-1", "movies", "The Odyssey", "no_match", coverage="complete", evidence=(evidence,))
        unavailable = WatchResult("result-2", "watch-1", "movies", "The Odyssey", "unavailable", coverage="unavailable", reason="Inventory capture timed out")
        self.assertEqual(no_match.outcome, "no_match")
        self.assertEqual(unavailable.outcome, "unavailable")
        self.assertNotEqual(no_match.outcome, unavailable.outcome)

    def test_result_requires_evidence_values_and_timezone(self):
        with self.assertRaises(ValueError):
            Evidence("AMC", "seat-inventory", "")
        with self.assertRaises(ValueError):
            Evidence("AMC", "seat-inventory", "Captured", captured_at=datetime(2026, 9, 2))


if __name__ == "__main__":
    unittest.main()
