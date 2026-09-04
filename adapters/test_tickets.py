import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


TICKET_WATCHER_ROOT = Path(__file__).parents[1] / "modules" / "ticket-watcher"
if str(TICKET_WATCHER_ROOT) not in sys.path:
    sys.path.insert(0, str(TICKET_WATCHER_ROOT))

from core.contracts import WatchDefinition
from ticket_watcher.models import Listing, Match
from tickets import TicketWatcherAdapter, normalize_ticket_job


def make_watch(**criteria):
    values = {"quantity": 4, "must_be_together": True}
    values.update(criteria)
    return WatchDefinition("watch-1", "tickets", "Lakers Warriors", criteria=values)


def make_match(**changes):
    values = dict(
        source="Ticketmaster browser",
        event_id="event-1",
        event_name="Los Angeles Lakers vs Golden State Warriors",
        event_url="https://example.test/event-1",
        venue="Crypto.com Arena",
        city="Los Angeles",
        starts_at=datetime(2026, 10, 10, 3, 0, tzinfo=timezone.utc),
        currency="USD",
        price_each=120.0,
        quantity_available=4,
        seats_together=True,
        fees_included=True,
    )
    values.update(changes.pop("listing", {}))
    listing = Listing(**values)
    return Match(listing=listing, estimated_order_total=480.0, score=93.0, notes=changes.pop("notes", ()))


class TicketAdapterTests(unittest.TestCase):
    def test_fully_supported_offer_is_verified_with_destination(self):
        results = normalize_ticket_job(
            {"id": "job-1", "status": "done", "sources_total": 1, "sources_checked": 1, "matches": [make_match()]},
            make_watch(),
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].outcome, "match")
        self.assertEqual(results[0].verification, "verified")
        self.assertEqual(results[0].coverage, "complete")
        self.assertEqual(results[0].destination_url, "https://example.test/event-1")
        self.assertIn("fees included", results[0].evidence[0].summary)

    def test_event_level_offer_stays_unverified_when_fees_or_inventory_are_unknown(self):
        results = normalize_ticket_job(
            {
                "id": "job-2",
                "status": "done",
                "sources_total": 1,
                "sources_checked": 1,
                "matches": [
                    make_match(
                        listing={"quantity_available": None, "seats_together": None, "fees_included": None},
                        notes=("Fees are unknown; total is an estimate", "Seat adjacency is not supplied by this source"),
                    )
                ],
            },
            make_watch(),
        )
        self.assertEqual(results[0].outcome, "match")
        self.assertEqual(results[0].verification, "unverified")
        self.assertIn("estimate", results[0].reason)

    def test_complete_no_match_is_truthful(self):
        results = normalize_ticket_job(
            {
                "id": "job-3",
                "status": "done",
                "sources_total": 2,
                "sources_checked": 2,
                "message": "No qualifying ticket offers",
            },
            make_watch(),
        )
        self.assertEqual(results[0].outcome, "no_match")
        self.assertEqual(results[0].verification, "verified")
        self.assertEqual(results[0].coverage, "complete")
        self.assertIn("2 of 2", results[0].evidence[0].summary)

    def test_partial_no_match_is_unverified(self):
        results = normalize_ticket_job(
            {"id": "job-4", "status": "done", "sources_total": 3, "sources_checked": 1},
            make_watch(),
        )
        self.assertEqual(results[0].outcome, "no_match")
        self.assertEqual(results[0].verification, "unverified")
        self.assertEqual(results[0].coverage, "partial")

    def test_in_progress_and_error_states_are_not_no_match(self):
        checking = normalize_ticket_job({"id": "job-5", "status": "checking"}, make_watch())[0]
        self.assertEqual(checking.outcome, "unavailable")
        self.assertEqual(checking.coverage, "unknown")

        failed = normalize_ticket_job({"id": "job-6", "status": "error", "message": "Ticketmaster blocked"}, make_watch())[0]
        self.assertEqual(failed.outcome, "error")
        self.assertEqual(failed.coverage, "unavailable")
        self.assertIn("blocked", failed.reason)

    def test_adapter_uses_injected_provider_at_run_boundary(self):
        adapter = TicketWatcherAdapter(
            lambda watch: {"id": watch.watch_id, "status": "done", "sources_total": 0, "sources_checked": 0}
        )
        results = list(adapter.run_once(make_watch()))
        self.assertEqual(adapter.module_name, "tickets")
        self.assertEqual(results[0].module, "tickets")
        self.assertEqual(results[0].outcome, "no_match")


if __name__ == "__main__":
    unittest.main()
