@echo off
cd /d "%~dp0"
set LOG=reports\wheel_dip_log.txt
py -3 femm_wheel_dip.py > "%LOG%" 2>&1
if errorlevel 1 python femm_wheel_dip.py >> "%LOG%" 2>&1
echo BATCH_FINISHED >> "%LOG%"
