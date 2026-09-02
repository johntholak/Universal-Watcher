#!/bin/bash
set -u
cd "$(dirname "$0")"

PYTHON=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON="python"
fi

if [ -z "$PYTHON" ]; then
  echo
  echo "HUNT needs Python 3 to run the local deal-verification engine."
  echo "Python 3 was not found on this Mac."
  echo
  echo "Install Python 3, then double-click start_hunt.command again."
  echo
  read -r -p "Press RETURN to close."
  exit 1
fi

echo "Starting HUNT with $PYTHON..."
"$PYTHON" server.py
STATUS=$?

echo
if [ $STATUS -ne 0 ]; then
  echo "HUNT exited with status $STATUS."
  read -r -p "Press RETURN to close."
fi
exit $STATUS
