#!/bin/bash
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

if command -v python3.14 >/dev/null 2>&1; then
  PYTHON_BASE="$(command -v python3.14)"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BASE="$(command -v python3)"
else
  echo ""
  echo "Python 3 was not found."
  echo "Install Python 3.14 from python.org, then run this file again."
  echo ""
  read -r -p "Press Return to close..."
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "Creating Seat Watcher's local Python environment..."
  "$PYTHON_BASE" -m venv .venv || exit 1
fi

echo "Installing/updating Seat Watcher dependencies..."
.venv/bin/python -m pip install -r requirements.txt || exit 1

echo "Installing Playwright Chromium..."
.venv/bin/python -m playwright install chromium || exit 1

echo "Running offline regression tests..."
.venv/bin/python -m unittest discover -s tests -v || exit 1

echo "Starting Seat Watcher..."
.venv/bin/python seat_watcher_premium.py
STATUS=$?

if [ "$STATUS" -ne 0 ]; then
  echo ""
  echo "Seat Watcher exited with status $STATUS."
  read -r -p "Press Return to close..."
fi

exit "$STATUS"
