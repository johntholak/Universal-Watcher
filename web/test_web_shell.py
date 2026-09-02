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
        for marker in ("Universal Watcher", "Active watches", "Recent activity", "Create a watch", "data-module=\"movies\"", "create-dialog"):
            self.assertIn(marker, html)

    def test_javascript_has_safe_draft_flow(self):
        javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("Local preview API", javascript)
        self.assertIn("Browser-only preview", javascript)
        self.assertIn("escapeHtml", javascript)
        self.assertIn("addDraft", javascript)


if __name__ == "__main__":
    unittest.main()
