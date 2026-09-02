@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py server.py
  goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
  python server.py
  goto :eof
)
echo.
echo HUNT V4 needs Python to run the local deal-verification engine.
echo Python was not found on this computer.
echo.
pause
