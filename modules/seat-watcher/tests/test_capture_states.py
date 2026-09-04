"""Exercise the real async engine without AMC access or GUI windows."""
import asyncio
import json
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from amc_showtime_api import AmcUnauthorizedVendorKey
from seat_watcher_v44 import (
    DEFAULT_SETTINGS, WatcherEngine, discover_amc_theaters_for_location,
    verify_seats_against_rendered_map,
    diagnostic_url,
)


THEATER = {"name": "AMC Test", "slug": "amc-test", "distance": 0,
           "theater_url": "https://www.amctheatres.com/movie-theatres/test/amc-test"}
SHOWTIME = {"id": "123", "theater": "AMC Test", "date": "2026-09-04",
            "time": "6:00pm", "format": "IMAX", "distance": 0,
            "url": "https://www.amctheatres.com/showtimes/123/seats"}


def engine():
    settings = dict(DEFAULT_SETTINGS, date_mode="SPECIFIC DATE", date_start="2026-09-04",
                    seats_required=4, minimum_row=5)
    with patch("seat_watcher_v44.load_amc_vendor_key", return_value=""):
        return WatcherEngine(settings, Mock(), Mock(), threading.Event(), Mock())


def fake_browser(page):
    context = SimpleNamespace(new_page=AsyncMock(return_value=page), close=AsyncMock())
    return SimpleNamespace(new_context=AsyncMock(return_value=context)), context


class CaptureStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_navigation_error_and_http_denial_count_as_unavailable(self):
        for failure in (RuntimeError("network failed"), SimpleNamespace(status=403)):
            watcher = engine()
            page = SimpleNamespace(goto=AsyncMock(), close=AsyncMock())
            if isinstance(failure, Exception):
                page.goto.side_effect = failure
            else:
                page.goto.return_value = failure
            browser, context = fake_browser(page)
            self.assertEqual(await watcher.discover_theater(
                browser, THEATER, "2026-09-04", asyncio.Semaphore(1)), [])
            self.assertEqual(len(watcher.discovery_failures), 1)
            context.close.assert_awaited_once()

    async def test_missing_date_is_not_verified_empty(self):
        watcher = engine()
        selector = SimpleNamespace(wait_for=AsyncMock())
        page = SimpleNamespace(goto=AsyncMock(return_value=SimpleNamespace(status=200)),
                               locator=Mock(return_value=selector),
                               wait_for_function=AsyncMock(), close=AsyncMock())
        browser, _ = fake_browser(page)
        with patch("seat_watcher_v44.DISCOVERY_TIMEOUT", 0):
            await watcher.discover_theater(browser, THEATER, "2026-09-04", asyncio.Semaphore(1))
        self.assertEqual(watcher.discovery_failures[0][2], "Requested date not selectable")

    async def test_unexpected_discovery_task_failure_is_counted(self):
        watcher = engine()
        watcher.discover_theater = AsyncMock(side_effect=RuntimeError("task failed"))
        self.assertEqual(await watcher.discover_all_theaters(None, [THEATER]), [])
        self.assertEqual(len(watcher.discovery_failures), 1)

    async def test_auth_rejection_does_not_invent_activation_date(self):
        watcher = engine()
        watcher.amc_api_client = Mock()
        watcher.amc_api_client.resolve_theatre_id.side_effect = AmcUnauthorizedVendorKey()
        browser = SimpleNamespace(new_context=AsyncMock(side_effect=RuntimeError("offline")))
        await watcher.discover_theater(browser, THEATER, "2026-09-04", asyncio.Semaphore(1))
        self.assertIsNone(watcher.amc_api_client)
        messages = " ".join(str(c.args[0]) for c in watcher.emit.call_args_list)
        self.assertIn("reason is not established", messages)
        self.assertNotIn("Thursday", messages)

    async def test_official_theatre_id_avoids_slug_resolution(self):
        watcher = engine()
        watcher.amc_api_client = Mock()
        watcher.amc_api_client.list_showtimes.return_value = []
        result = await watcher.discover_theater(
            None, dict(THEATER, amc_theatre_id=123), "2026-09-04", asyncio.Semaphore(1))
        self.assertEqual(result, [])
        watcher.amc_api_client.resolve_theatre_id.assert_not_called()
        self.assertEqual(watcher.discovery_failures, [])

    async def test_seat_states_and_http_error_body(self):
        for status, available, expected in ((200, True, "match"),
                                           (200, False, "captured_no_match"),
                                           (403, True, "unavailable"),
                                           (429, True, "unavailable")):
            with self.subTest(status=status, available=available):
                watcher = engine()
                seats = [{"available": available, "column": n, "row": 5,
                          "name": f"F{n}"} for n in range(1, 5)]
                response = SimpleNamespace(url=SHOWTIME["url"], status=status,
                    headers={"content-type": "application/json"},
                    body=AsyncMock(return_value=json.dumps(seats).encode()))
                page = SimpleNamespace(on=Mock(), remove_listener=Mock(), close=AsyncMock(),
                    wait_for_load_state=AsyncMock(), wait_for_timeout=AsyncMock())
                controls = [{"name": s["name"], "label": f"Traditional Seat {s['name']}",
                             "disabled": not available} for s in seats]
                seat_map = SimpleNamespace(wait_for=AsyncMock(),
                    get_by_role=Mock(return_value=SimpleNamespace(evaluate_all=AsyncMock(return_value=controls))))
                page.get_by_role = Mock(return_value=seat_map)

                async def navigate(*args, **kwargs):
                    page.on.call_args.args[1](response)
                    return response

                page.goto = navigate
                browser, context = fake_browser(page)
                with patch("seat_watcher_v44.SEAT_CAPTURE_WAIT_SECONDS", 0):
                    result = await watcher.check_showtime(browser, SHOWTIME, asyncio.Semaphore(1))
                self.assertEqual(result["inventory_status"], expected)
                if status in (403, 429):
                    response.body.assert_not_awaited()
                    again = await watcher.check_showtime(browser, SHOWTIME, asyncio.Semaphore(1))
                    self.assertEqual(again["inventory_status"], "unavailable")
                    browser.new_context.assert_awaited_once()  # no additional request after denial
                else:
                    self.assertEqual(result["inventory_seat_count"], 4)
                if expected == "match":
                    self.assertEqual(result["seats"], ["F1", "F2", "F3", "F4"])
                page.remove_listener.assert_called_once()
                context.close.assert_awaited_once()

    async def test_failed_browser_start_is_inventory_unavailable(self):
        watcher = engine()
        browser = SimpleNamespace(new_context=AsyncMock(side_effect=RuntimeError("offline")))
        result = await watcher.check_showtime(browser, SHOWTIME, asyncio.Semaphore(1))
        self.assertEqual(result["inventory_status"], "unavailable")

    async def test_authoritative_empty_radius_does_not_fall_back_to_maps(self):
        with patch("seat_watcher_v44.geocode_location", return_value=(34, -118, "Test")), \
             patch("seat_watcher_v44.load_amc_vendor_key", return_value="test-key"), \
             patch("seat_watcher_v44.AmcShowtimeClient.list_theatres", return_value=[]), \
             patch("seat_watcher_v44.overpass_find_amc_theaters") as maps:
            result = await discover_amc_theaters_for_location("Test", 10)
        maps.assert_not_called()
        self.assertEqual(result, {"theaters": [], "lat": 34, "lon": -118,
                                  "display_name": "Test", "location_query": "Test"})


class RenderedInventoryTests(unittest.TestCase):
    def setUp(self):
        self.seats = [{"name": f"D{i}", "available": True, "row": 5, "column": i}
                      for i in range(1, 5)]
        self.controls = [{"name": s["name"], "label": f"AMC Club Rocker {s['name']}",
                          "disabled": False} for s in self.seats]

    def test_accessible_spaces_cannot_create_ordinary_four_seat_match(self):
        self.controls[1]["label"] = "Wheelchair Companion AMC Club Rocker D2"
        self.controls[2]["label"] = "Wheelchair Space D3"
        self.controls[3]["label"] = "Wheelchair Space D4"
        verified = verify_seats_against_rendered_map(self.seats, self.controls)
        self.assertIsNone(engine().find_consecutive_seats(verified))
        self.assertTrue(all(s["available"] for s in self.seats))  # original parser output untouched

    def test_complete_ordinary_group_still_matches(self):
        verified = verify_seats_against_rendered_map(self.seats, self.controls)
        self.assertEqual([s["name"] for s in engine().find_consecutive_seats(verified)],
                         ["D1", "D2", "D3", "D4"])

    def test_missing_or_disagreeing_map_is_not_no_match(self):
        for controls in ([], self.controls + [dict(self.controls[0])],
                         [dict(self.controls[0], disabled=True)]):
            with self.subTest(controls=controls), self.assertRaises(ValueError):
                verify_seats_against_rendered_map(self.seats, controls)
        with self.assertRaises(ValueError):
            verify_seats_against_rendered_map(self.seats[:-1], self.controls)

    def test_conflicting_snapshots_are_not_merged_into_false_availability(self):
        with self.assertRaises(ValueError):
            verify_seats_against_rendered_map(
                self.seats + [dict(self.seats[0], available=False)], self.controls)

    def test_unnamed_gaps_do_not_count_as_conflicting_physical_seats(self):
        gaps = [{"name": "", "available": False, "row": 1, "column": 1},
                {"name": "", "available": False, "row": 2, "column": 1}]
        result = verify_seats_against_rendered_map(gaps + self.seats, self.controls)
        self.assertEqual(len(result), 4)

    def test_diagnostic_urls_remove_queue_and_session_tokens(self):
        self.assertEqual(diagnostic_url("https://www.amctheatres.com/showtimes/123/seats?queueittoken=secret#token"),
                         "https://www.amctheatres.com/showtimes/123/seats")

    def test_streamed_layout_round_trip_keeps_gap_and_accessibility_metadata(self):
        records = [{"name": "", "available": False, "row": 1, "column": 1,
                    "shouldDisplay": False}, *self.seats,
                   {"name": "", "available": False, "row": 2, "column": 1,
                    "shouldDisplay": False}]
        escaped = json.dumps(records).replace('"', '\\"')
        watcher = engine()
        parsed = watcher.parse_seats_from_bytes(f'<script>{escaped}</script>'.encode())
        verified = verify_seats_against_rendered_map(parsed, self.controls)
        self.assertEqual(len(verified), 4)
        self.assertEqual([s["name"] for s in watcher.find_consecutive_seats(verified)],
                         ["D1", "D2", "D3", "D4"])


if __name__ == "__main__":
    unittest.main()
