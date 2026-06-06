@echo off
setlocal
cd /d "%~dp0.."
set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not exist "%PY%" set "PY=%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0ToolsetDashboardE2E.harness.py"
if errorlevel 1 exit /b 1
echo RUN_TOOLSET_DASHBOARD_E2E: ALL PASS
exit /b 0
