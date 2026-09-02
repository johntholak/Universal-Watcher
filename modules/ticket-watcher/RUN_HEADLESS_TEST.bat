@echo off
cd /d "%~dp0"
python ticketmaster_live_watcher.py --once
echo.
pause
