#!/bin/bash
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo ""
  echo "Seat Watcher needs its local Python environment."
  echo ""
  echo "From Terminal in this folder, run:"
  echo "  python3.14 -m venv .venv"
  echo "  .venv/bin/python -m pip install -r requirements.txt"
  echo "  .venv/bin/python -m playwright install chromium"
  echo ""
  read -r -p "Press Return to close..."
  exit 1
fi

"$PYTHON" seat_watcher_premium.py
STATUS=$?

if [ "$STATUS" -ne 0 ]; then
  echo ""
  echo "Seat Watcher exited with status $STATUS."
  read -r -p "Press Return to close..."
fi

exit "$STATUS"
