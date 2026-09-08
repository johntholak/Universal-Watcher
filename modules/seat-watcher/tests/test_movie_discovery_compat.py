import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from movie_discovery_compat import (
    candidate_showtime_urls,
    extract_link_title,
    h1_looks_like_movie_title,
    heading_looks_like_movie_title,
)


class MovieDiscoveryCompatTests(unittest.TestCase):
    def test_legacy_link_title_behavior_is_preserved(self):
        self.assertEqual(
            extract_link_title("The Odyssey\n2 HR 52 MIN\nR"),
            "The Odyssey",
        )

    def test_current_h1_movie_title_is_accepted_without_sibling_runtime(self):
        self.assertTrue(h1_looks_like_movie_title("The Odyssey", "AMC Topanga 12"))

    def test_showtimes_h1_is_not_a_movie(self):
        self.assertFalse(h1_looks_like_movie_title("Showtimes", "AMC Topanga 12"))

    def test_trailer_heading_is_not_a_movie(self):
        self.assertFalse(
            h1_looks_like_movie_title(
                "The Odyssey Trailers and Info", "AMC Topanga 12"
            )
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
            "https://www.amctheatres.com/movie-theatres/los-angeles/amc-topanga-12/showtimes",
            urls,
        )

    def test_fallbrook_has_current_canonical_fallback(self):
        urls = candidate_showtime_urls(
            {"name": "AMC Fallbrook 7", "slug": "amc-fallbrook-7"}
        )
        self.assertIn(
            "https://www.amctheatres.com/movie-theatres/west-hills/amc-fallbrook-7/showtimes",
            urls,
        )

    def test_northridge_and_porter_ranch_current_routes_are_available(self):
        north = candidate_showtime_urls(
            {"name": "AMC Northridge 10", "slug": "amc-northridge-10"}
        )
        porter = candidate_showtime_urls(
            {"name": "AMC Porter Ranch 9", "slug": "amc-porter-ranch-9"}
        )
        self.assertIn(
            "https://www.amctheatres.com/movie-theatres/los-angeles/amc-northridge-10/showtimes",
            north,
        )
        self.assertIn(
            "https://www.amctheatres.com/movie-theatres/los-angeles/amc-porter-ranch-9/showtimes",
            porter,
        )


if __name__ == "__main__":
    unittest.main()
