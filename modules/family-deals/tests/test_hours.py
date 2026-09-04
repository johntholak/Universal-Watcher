import unittest
from datetime import datetime

from server import parse_simple_opening_hours


class OpeningHoursTests(unittest.TestCase):
    def test_common_weekday_hours_report_dinner_open(self):
        at = datetime(2026, 9, 7, 9, 0)  # Monday
        self.assertTrue(parse_simple_opening_hours("Mo-Fr 11:00-22:00; Sa-Su 12:00-23:00", at))

    def test_explicit_closed_day_is_false(self):
        monday = datetime(2026, 9, 7, 9, 0)
        saturday = datetime(2026, 9, 12, 9, 0)
        spec = "Mo off; Tu-Fr 11:00-22:00"
        self.assertFalse(parse_simple_opening_hours(spec, monday))
        self.assertIsNone(parse_simple_opening_hours(spec, saturday))

    def test_missing_day_is_unknown_not_closed(self):
        sunday = datetime(2026, 9, 13, 9, 0)
        self.assertIsNone(parse_simple_opening_hours("Mo-Fr 11:00-22:00", sunday))

    def test_overnight_hours_are_supported(self):
        monday = datetime(2026, 9, 7, 9, 0)
        self.assertTrue(parse_simple_opening_hours("Mo 17:00-02:00", monday))

    def test_twelve_hour_and_compact_times_are_supported(self):
        monday = datetime(2026, 9, 7, 9, 0)
        self.assertTrue(parse_simple_opening_hours("Mon 11 AM-10 PM", monday))
        self.assertTrue(parse_simple_opening_hours("Mo 1100-2200", monday))

    def test_unsupported_syntax_remains_unknown(self):
        monday = datetime(2026, 9, 7, 9, 0)
        self.assertIsNone(parse_simple_opening_hours("Mo by appointment", monday))


if __name__ == "__main__":
    unittest.main()
