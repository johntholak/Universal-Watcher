import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from movie_discovery_compat import (
    candidate_showtime_urls,
    extract_link_title,
    heading_looks_like_movie_title,
)


class MovieDiscoveryCompatTests(unittest.TestCase):
    def test_legacy_link_title_behavior_is_preserved(self):
        self.assertEqual(
            extract_link_title("The Odyssey\n2 HR 52 MIN\nR"),
            "The Odyssey",
        )

    def test_rendered_heading_with_runtime_is_movie_title(self):
        self.assertTrue(
            heading_looks_like_movie_title(
                "The Odyssey",
                "2 HR 52 MIN\nR\nAMC Topanga 12",
                "AMC Topanga 12",
            )
        )

    def test_format_heading_is_not_movie_title(self):
        self.assertFalse(
            heading_looks_like_movie_title(
                "IMAX with Laser at AMC: EXTRAORDINARY AWAITS",
                "AMC Artisan Films\nReserved Seating\n6:45pm",
                "AMC Topanga 12",
            )
        )

    def test_theater_heading_is_not_movie_title(self):
        self.assertFalse(
            heading_looks_like_movie_title(
                "AMC Topanga 12",
                "2 HR 52 MIN\nR",
                "AMC Topanga 12",
            )
        )

    def test_topanga_keeps_saved_route_then_current_canonical_fallback(self):
        urls = candidate_showtime_urls(
            {
                "name": "AMC Topanga 12",
                "slug": "amc-topanga-12",
                "theater_url": "https://www.amctheatres.com/movie-theatres/undefined/amc-topanga-12",
            }
        )
        self.assertEqual(
            urls[0],
            "https://www.amctheatres.com/movie-theatres/undefined/amc-topanga-12/showtimes",
        )
        self.assertIn(
            "https://www.amctheatres.com/movie-theatres/los-angeles/amc-dine-in-topanga-12/showtimes",
            urls,
        )

    def test_fallbrook_has_current_canonical_fallback(self):
        urls = candidate_showtime_urls(
            {"name": "AMC Fallbrook 7", "slug": "amc-fallbrook-7"}
        )
        self.assertIn(
            "https://www.amctheatres.com/movie-theatres/amc-fallbrook-7/amc-fallbrook-7/showtimes",
            urls,
        )


if __name__ == "__main__":
    unittest.main()
