import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ManageEntryPointTests(unittest.TestCase):
    def test_movies_launches_proven_v44_ui_directly(self):
        text = (ROOT / "manage.py").read_text(encoding="utf-8")
        self.assertIn(
            "'movies': ('modules/seat-watcher', 'seat_watcher_premium.py', [])",
            text,
        )
        self.assertNotIn("run_movies_compat.py", text)


if __name__ == "__main__":
    unittest.main()
