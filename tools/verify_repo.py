from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

required = [
    "AGENTS.md",
    "PRODUCT_VISION.md",
    "PROJECT_STATUS.md",
    "RUNBOOK.md",
    "modules/family-deals/server.py",
    "modules/family-deals/CODEX_HANDOFF.md",
    "modules/ticket-watcher/README.md",
    "modules/ticket-watcher/START_TICKET_WATCHER.bat",
    "modules/seat-watcher/seat_watcher_v44.py",
    "modules/seat-watcher/amc_showtime_api.py",
    "modules/seat-watcher/live_amc_diagnostic.py",
    "modules/seat-watcher/.env.example",
    "modules/seat-watcher/tests/test_amc_showtime_api.py",
    "modules/seat-watcher/run_v44.command",
    "modules/seat-watcher/requirements.txt",
    "web/index.html",
    "web/styles.css",
    "web/app.js",
    "web/test_web_shell.py",
    "web/server.py",
    "web/test_server.py",
    "core/contracts.py",
    "core/test_contracts.py",
    "core/__init__.py",
]

missing = [p for p in required if not (ROOT / p).exists()]

print("Universal Watcher repo:", ROOT)
print("Required baseline files:", len(required))
print("Missing:", len(missing))

if missing:
    for p in missing:
        print(" -", p)
    sys.exit(1)

seat_engine = ROOT / "modules/seat-watcher/seat_watcher_v44.py"
if seat_engine.exists():
    print("Seat Watcher source: RECONSTRUCTED BUILD PRESENT")
else:
    print("Seat Watcher source: MISSING")

print("Baseline structure check passed.")
