@echo off
REM ============================================================
REM  Sets up Windows Task Scheduler to run the scraper daily.
REM  Run this script ONCE as Administrator.
REM ============================================================

set TASK_NAME=FDP_Scraper_Agent
set SCRIPT_PATH=%~dp0run_scraper.bat
set RUN_TIME=08:00

echo Creating scheduled task: %TASK_NAME%
echo Script: %SCRIPT_PATH%
echo Schedule: Daily at %RUN_TIME%
echo.

schtasks /create /tn "%TASK_NAME%" /tr "\"%SCRIPT_PATH%\"" /sc daily /st %RUN_TIME% /f /rl HIGHEST

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Task created successfully!
    echo It will run daily at %RUN_TIME%.
    echo.
    echo To change the time, edit RUN_TIME in this script and re-run,
    echo or use Task Scheduler GUI: taskschd.msc
) else (
    echo.
    echo Failed to create task. Make sure you run this as Administrator.
)

pause
