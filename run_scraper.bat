@echo off
REM ============================================================
REM  FDP Scraper Agent — Launcher Script
REM  Loads credentials and runs the scraper.
REM  Used by Windows Task Scheduler for daily automation.
REM ============================================================

cd /d "%~dp0"

REM Create logs directory
if not exist "logs" mkdir logs

REM Load credentials from .env file
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    set "%%a=%%b"
)

REM Run the scraper
.venv\Scripts\python.exe scraper.py >> "logs\run_%date:~-4%-%date:~4,2%-%date:~7,2%.log" 2>&1

echo [%date% %time%] Scraper run completed >> logs\run_log.txt
