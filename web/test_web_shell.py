import unittest
from pathlib import Path


WEB_ROOT = Path(__file__).parent


class WebShellTests(unittest.TestCase):
    def test_shell_assets_exist(self):
        self.assertTrue((WEB_ROOT / "index.html").is_file())
        self.assertTrue((WEB_ROOT / "styles.css").is_file())
        self.assertTrue((WEB_ROOT / "app.js").is_file())

    def test_index_has_core_shell_surfaces(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        for marker in ("UNIVERSAL WATCHER", "Active Watches", "Recent Results", "My Watches", "result-list", "Find Movie Seats", "data-view=\"movies\"", "movie-search-form"):
            self.assertIn(marker, html)

    def test_movies_flow_preserves_approved_controls(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        for marker in (
            "Find Movies", "Use My Location", "movie-radius", "Find Theaters",
            "theater-list", "Next best available", "Specific date", "Date range",
            "earliest-time", "latest-time", "Seats together", "Minimum row",
            "IMAX 70MM", "Priorities", "Advanced Options", "Search for Seats",
            "Save as Watch",
        ):
            self.assertIn(marker, html)

    def test_shell_uses_locked_visual_language_and_hides_shelved_modules(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        css = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertNotIn('data-view="tickets"', html)
        self.assertNotIn('data-view="jobs"', html)
        for marker in ("--bg:#050b18", "--purple:#7367ff", "--green:#31df88", ".workflow-card", ".search-summary"):
            self.assertIn(marker, css)

    def test_javascript_has_safe_draft_flow(self):
        javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("Local preview API unavailable", javascript)
        self.assertIn("Provider request skipped", javascript)
        self.assertIn("escapeHtml", javascript)
        self.assertIn("addDraft", javascript)
        self.assertIn("data-watch-action", javascript)
        self.assertIn('method: "PATCH"', javascript)
        self.assertIn("/api/results", javascript)
        self.assertIn("movieCriteria", javascript)
        self.assertIn("this is an unavailable provider state, not a no-match result", javascript)


if __name__ == "__main__":
    unittest.main()
