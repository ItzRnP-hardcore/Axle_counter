@echo off
REM Double-clickable wrapper for run_all.py -- runs the whole pipeline.
REM Console output stays live so you can watch the FEMM stages progress.
REM Pass any run_all.py flag straight through, e.g.:
REM     run_all.bat --list
REM     run_all.bat --skip-femm
REM     run_all.bat --with-optional
cd /d "%~dp0"

REM Prefer the py launcher; fall back to whatever "python" resolves to.
where py >nul 2>&1
if errorlevel 1 (
    python run_all.py %*
) else (
    py -3 run_all.py %*
)
if errorlevel 1 goto :failed

echo.
echo Pipeline finished. See reports\ and reports\sanity_check_report.md
pause
exit /b 0

:failed
echo.
echo *** A STAGE FAILED -- see the output above. ***
pause
exit /b 1
