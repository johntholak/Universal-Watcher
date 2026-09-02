"""Small UI-adjacent regressions that do not launch a window."""
import unittest

from seat_watcher_premium import SeatWatcherPremiumGUI


class PremiumUIContractTests(unittest.TestCase):
    def test_touchpad_delta_uses_low_16_bits_for_vertical_axis(self):
        # dx=7 in high 16 bits, dy=-3 in low 16 bits
        packed = (7 << 16) | ((-3) & 0xFFFF)
        self.assertEqual(SeatWatcherPremiumGUI._decode_touchpad_delta(packed), (7, -3))

    def test_touchpad_delta_positive_vertical(self):
        packed = ((-4) & 0xFFFF) << 16 | 5
        self.assertEqual(SeatWatcherPremiumGUI._decode_touchpad_delta(packed), (-4, 5))


if __name__ == "__main__":
    unittest.main()
