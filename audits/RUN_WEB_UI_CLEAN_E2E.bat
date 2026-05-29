@echo off
setlocal
cd /d "%~dp0.."
set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0WebUICleanE2E.harness.py"
if errorlevel 1 exit /b 1
echo RUN_WEB_UI_CLEAN_E2E: ALL PASS
exit /b 0
