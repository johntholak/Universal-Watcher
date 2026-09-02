@echo off
cd /d "%~dp0"
python ticketmaster_live_watcher.py
if errorlevel 1 (
  echo.
  echo Ticket Watcher could not start. Read the setup error above.
  pause
)
