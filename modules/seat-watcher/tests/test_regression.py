"""Fast behavior-contract tests; no network or browser calls."""
import unittest
from datetime import date
from unittest.mock import patch

from seat_watcher_v44 import (
    DEFAULT_SETTINGS,
    clean_theater_list,
    dated_request_was_blocked,
    extract_date_option_dates,
    format_matches,
    identify_format,
    inclusive_date_strings,
    load_amc_vendor_key,
    movie_similarity,
    normalize_amc_api_showtimes,
    next_best_should_stop,
    parse_date_value,
    resolve_date_option_value,
    results_fingerprint,
    showtime_results_are_meaningful,
    slugify_theater_name,
    summarize_inventory_results,
    time_to_minutes,
    WatcherEngine,
)


class HelperContractTests(unittest.TestCase):
    def test_time_parsing(self):
        self.assertEqual(time_to_minutes("12:00am"), 0)
        self.assertEqual(time_to_minutes("1:15pm"), 795)
        self.assertIsNone(time_to_minutes("evening"))

    def test_date_formats_and_inclusive_range(self):
        self.assertEqual(parse_date_value("08/27/2026"), date(2026, 8, 27))
        self.assertEqual(parse_date_value("2026-08-27"), date(2026, 8, 27))
        self.assertEqual(
            inclusive_date_strings(date(2026, 8, 27), date(2026, 8, 29)),
            ["2026-08-27", "2026-08-28", "2026-08-29"],
        )

    def test_movie_normalization_contract(self):
        self.assertEqual(movie_similarity("Spider-Man", "Spider Man"), 1.0)

    def test_format_matching_contract(self):
        self.assertTrue(format_matches("ANY", "Dolby Cinema"))
        self.assertTrue(format_matches("IMAX 70MM", "IMAX 70mm experience"))
        self.assertFalse(format_matches("IMAX", "IMAX 70MM"))
        self.assertTrue(format_matches("70MM", "70MM"))
        self.assertFalse(format_matches("70MM", "IMAX 70MM"))

    def test_standalone_70mm_detection(self):
        self.assertEqual(identify_format("Presented in 70mm"), "70MM")
        self.assertEqual(identify_format("IMAX 70mm"), "IMAX 70MM")
        self.assertEqual(identify_format("Dolby Cinema"), "DOLBY")

    def test_next_best_stopping_rule(self):
        self.assertFalse(next_best_should_stop(False, 0, 14))
        self.assertFalse(next_best_should_stop(True, 20, 34))
        self.assertTrue(next_best_should_stop(False, 0, 35))
        self.assertTrue(next_best_should_stop(True, 0, 35))

    def test_resolve_amc_date_option_value(self):
        options = [
            {"value": "", "text": "Today"},
            {"value": "2026-09-02", "text": "Wed, Sep 2"},
            {"value": "date=2026-09-03", "text": "Thu, Sep 3"},
            {"value": "opaque-token", "text": "Fri, Sep 4"},
        ]
        self.assertEqual(
            resolve_date_option_value(options, "2026-09-01", date(2026, 9, 1)),
            "",
        )
        self.assertEqual(
            resolve_date_option_value(options, "2026-09-02", date(2026, 9, 1)),
            "2026-09-02",
        )
        self.assertEqual(
            resolve_date_option_value(options, "2026-09-03", date(2026, 9, 1)),
            "date=2026-09-03",
        )
        self.assertEqual(
            resolve_date_option_value(options, "2026-09-04", date(2026, 9, 1)),
            "opaque-token",
        )

    def test_extract_amc_selectable_date_range(self):
        options = [
            {"value": "", "text": "Today"},
            {"value": "2026-09-05", "text": "Sat, Sep 5"},
            {"value": "opaque", "text": "Mon, Sep 7"},
            {"value": "date=2026-10-01", "text": "Thu, Oct 1"},
        ]
        self.assertEqual(
            extract_date_option_dates(options, date(2026, 9, 2)),
            [
                date(2026, 9, 2),
                date(2026, 9, 5),
                date(2026, 9, 7),
                date(2026, 10, 1),
            ],
        )

    def test_results_fingerprint_uses_showtime_links(self):
        first = results_fingerprint("6:00pm IMAX 70MM", ["/showtimes/111"])
        second = results_fingerprint("6:00pm IMAX 70MM", ["/showtimes/222"])
        self.assertNotEqual(first, second)

    def test_showtime_results_wait_for_links_or_explicit_empty_state(self):
        self.assertFalse(showtime_results_are_meaningful("Loading showtimes...", []))
        self.assertTrue(showtime_results_are_meaningful("The Odyssey", ["/showtimes/111"]))
        self.assertTrue(showtime_results_are_meaningful("No showtimes available", []))

    def test_inventory_failures_are_not_valid_no_seat_results(self):
        results = [
            {"inventory_status": "captured_no_match"},
            {"inventory_status": "unavailable"},
            RuntimeError("capture task failed"),
            {"inventory_status": "match", "seats": ["H10", "H11"]},
        ]
        matches, captured_no_match, unavailable, errors = summarize_inventory_results(results)
        self.assertEqual(len(matches), 1)
        self.assertEqual(captured_no_match, 1)
        self.assertEqual(unavailable, 2)
        self.assertEqual(errors, 1)

    def test_official_amc_seat_name_alias_is_parsed(self):
        watcher = object.__new__(WatcherEngine)
        seats = []
        watcher.walk_json(
            {"seats": [{
                "available": True,
                "column": 10,
                "row": 5,
                "seatName": "H10",
                "type": "CanReserve",
            }]},
            seats,
        )
        self.assertEqual(seats[0]["name"], "H10")
        self.assertTrue(seats[0]["available"])

    def test_blocked_dated_request_is_not_an_empty_showtime_result(self):
        responses = [
            (200, "https://www.amctheatres.com/showtimes"),
            (403, "https://www.amctheatres.com/showtimes?date=2026-09-03&_rsc=x"),
        ]
        self.assertTrue(dated_request_was_blocked(responses, "2026-09-03"))
        self.assertFalse(dated_request_was_blocked(responses, "2026-09-04"))

    def test_amc_api_records_use_existing_movie_format_and_time_filters(self):
        records = [
            {
                "id": 145681141,
                "movieName": "The Odyssey",
                "showDateTimeLocal": "2026-09-03T14:00:00",
                "attributes": [{"code": "IMAX70MM", "name": "IMAX 70MM"}],
                "isCanceled": False,
            },
            {
                "id": 999,
                "movieName": "Different Movie",
                "showDateTimeLocal": "2026-09-03T14:00:00",
                "attributes": [{"name": "IMAX 70MM"}],
            },
        ]
        results = normalize_amc_api_showtimes(
            records,
            {"name": "AMC Universal CityWalk 19", "distance": 1.5},
            "2026-09-03",
            "The Odyssey",
            "IMAX 70MM",
            12 * 60,
            18 * 60,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "145681141")
        self.assertEqual(results[0]["time"], "2:00pm")
        self.assertEqual(results[0]["discovery_source"], "AMC Showtime API")

    def test_amc_key_prefers_environment_without_exposing_it(self):
        with patch.dict("os.environ", {"AMC_VENDOR_KEY": "approved-test-key"}):
            self.assertEqual(load_amc_vendor_key(), "approved-test-key")

    def test_citywalk_canonical_slug(self):
        self.assertEqual(
            slugify_theater_name("AMC Universal CityWalk 19"),
            "universal-cinema-an-amc-theatre",
        )
        self.assertEqual(
            slugify_theater_name("Universal Cinema - an AMC Theatre"),
            "universal-cinema-an-amc-theatre",
        )

    def test_theater_cleanup(self):
        theaters = [
            {"name": "AMC Fallbrook 7", "lat": 34.20, "lon": -118.62, "distance": 4.0},
            {"name": "AMC Fallbrook 7", "lat": 34.21, "lon": -118.63, "distance": 3.5},
            {"name": "AMC", "lat": 34.1, "lon": -118.5, "distance": 1.0},
            {"name": "AMC Universal CityWalk 19", "lat": 34.1381, "lon": -118.3529},
            {"name": "", "lat": 0, "lon": 0},
        ]
        cleaned = clean_theater_list(theaters)
        self.assertEqual(len(cleaned), 2)
        fallbrook = next(t for t in cleaned if t["name"] == "AMC Fallbrook 7")
        self.assertEqual(fallbrook["distance"], 3.5)
        citywalk = next(t for t in cleaned if "Universal" in t["name"])
        self.assertEqual(citywalk["slug"], "universal-cinema-an-amc-theatre")

    def test_required_settings_schema(self):
        required = {
            "movie", "format", "earliest_time", "latest_time",
            "seats_required", "minimum_row", "search_radius_miles",
            "check_interval", "sound_alert", "open_browser_on_match",
            "search_center_name", "location_query", "movie_options",
            "date_mode", "date_start", "date_end", "next_best_days",
            "search_lat", "search_lon", "showtime_refresh_cycles",
            "enabled_theaters",
        }
        self.assertTrue(required.issubset(DEFAULT_SETTINGS))


if __name__ == "__main__":
    unittest.main()
