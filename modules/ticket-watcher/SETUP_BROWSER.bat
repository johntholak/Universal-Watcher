@echo off
cd /d "%~dp0"
echo Installing the browser diagnostic tools...
python -m pip install -r requirements.txt
if errorlevel 1 goto error
python -m playwright install chromium
if errorlevel 1 goto error
echo.
echo Setup completed successfully.
pause
exit /b 0

:error
echo.
echo Setup did not complete. Send a screenshot of the error.
pause
exit /b 1
