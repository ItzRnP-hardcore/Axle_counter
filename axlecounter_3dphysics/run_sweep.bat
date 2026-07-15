@echo off
cd /d "%~dp0"
echo Running full femm_sweep DOE (9 solves)... FEMM will open repeatedly.
set LOG=reports\femm_sweep_log.txt
py -3 femm_sweep.py > "%LOG%" 2>&1
if errorlevel 1 python femm_sweep.py >> "%LOG%" 2>&1
echo. >> "%LOG%"
echo BATCH_FINISHED >> "%LOG%"
echo Finished. See reports\coil_parameter_sweep_femm.csv
