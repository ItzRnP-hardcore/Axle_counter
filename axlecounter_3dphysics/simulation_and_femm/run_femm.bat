@echo off
cd /d "%~dp0"
echo Running the live FEMM validation solve (magnetostatic + time-harmonic)...
set LOG=..\reports\femm_run_once_log.txt
py -3 femm_run_once.py > "%LOG%" 2>&1
if errorlevel 1 python femm_run_once.py >> "%LOG%" 2>&1
echo. >> "%LOG%"
echo BATCH_FINISHED >> "%LOG%"
echo Finished. See ..\reports\femm_live_result.txt
