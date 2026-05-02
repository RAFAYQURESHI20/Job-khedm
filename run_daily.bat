@echo off
REM ─────────────────────────────────────────────────────────
REM  JobPulse — Daily Pipeline (Windows Task Scheduler)
REM  Schedule this script via Task Scheduler to run at 02:00
REM ─────────────────────────────────────────────────────────

SET SCRIPT_DIR=%~dp0
SET LOG_FILE=%SCRIPT_DIR%pipeline_log_%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%.txt

echo [%DATE% %TIME%] Starting JobPulse daily pipeline … >> "%LOG_FILE%"

cd /d "%SCRIPT_DIR%"

python run_daily_pipeline.py --sources all >> "%LOG_FILE%" 2>&1

IF %ERRORLEVEL% NEQ 0 (
    echo [%DATE% %TIME%] ERROR: Pipeline exited with code %ERRORLEVEL% >> "%LOG_FILE%"
) ELSE (
    echo [%DATE% %TIME%] Pipeline completed successfully. >> "%LOG_FILE%"
)

exit /b %ERRORLEVEL%
