@echo off
REM ============================================================
REM  FDP Scraper Agent — Daily Launcher Script
REM  Loads credentials from .env and runs the scraper.
REM  Scheduled via Windows Task Scheduler.
REM ============================================================

cd /d "%~dp0"

REM Create logs directory
if not exist "logs" mkdir logs

REM Load credentials from .env file (skip blank lines and comments)
for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" set "%%a=%%b"
)

REM Get date for log filename (YYYY-MM-DD) via PowerShell (wmic is removed on newer Windows)
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"`) do set "LOGDATE=%%I"
if "%LOGDATE%"=="" set "LOGDATE=%date:~-4%-%date:~3,2%-%date:~0,2%"

echo [%LOGDATE% %time%] Starting scraper run... >> logs\run_log.txt

REM Run the scraper
.venv\Scripts\python.exe scraper.py >> "logs\run_%LOGDATE%.log" 2>&1
set "EXITCODE=%ERRORLEVEL%"

echo [%LOGDATE% %time%] Scraper run completed (exit code: %EXITCODE%) >> logs\run_log.txt
exit /b %EXITCODE%
