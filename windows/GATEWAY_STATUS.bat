@echo off
setlocal
cd /d "%~dp0.."
set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not exist "%PY%" (
  echo ERROR: hermes-env niet gevonden. Draai windows\REPAIR_PYTHON.bat
  exit /b 1
)
"%PY%" -m hermes_cli_entry gateway status
exit /b %ERRORLEVEL%
