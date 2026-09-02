@echo off
setlocal
cd /d "%~dp0"
title Seat Watcher V44

py -c "import customtkinter" >nul 2>nul
if errorlevel 1 py -m pip install customtkinter

py -c "import playwright" >nul 2>nul
if errorlevel 1 py -m pip install playwright

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
py seat_watcher_premium.py

echo.
echo Program closed.
pause
