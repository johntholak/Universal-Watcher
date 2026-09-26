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

    def test_movies_launch_scripts_target_existing_entrypoints(self):
        module = ROOT / "modules" / "seat-watcher"
        launchers = (
            "run_v44.command", "setup_and_run_v44.command",
            "run_v44.bat", "setup_and_run_v44.bat",
        )
        for name in launchers:
            with self.subTest(launcher=name):
                source = (module / name).read_text(encoding="utf-8")
                self.assertIn("seat_watcher_premium.py", source)
                self.assertNotIn("run_movies_compat.py", source)
                self.assertTrue((module / "seat_watcher_premium.py").is_file())


if __name__ == "__main__":
    unittest.main()
