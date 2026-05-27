@echo off
setlocal
cd /d "%~dp0.."

set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not exist "%PY%" set "PY=%~dp0..\..\Hermes_agent_Windows\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo Using: %PY%
"%PY%" -m pytest tests\plugins\test_codebase_viz_plugin.py -q --tb=short -o "addopts="
set "EC=%ERRORLEVEL%"
if %EC% neq 0 exit /b %EC%
echo RUN_CODEBASE_VIZ_UNIT_TESTS: ALL PASS
exit /b 0
