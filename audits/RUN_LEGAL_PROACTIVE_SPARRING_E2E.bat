@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul

set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not exist "%PY%" set "PY=python"

echo [INFO] Legal Proactive Sparring E2E (parallelle invalshoeken + config repair + legal USER seed)...
"%PY%" "%~dp0LegalProactiveSparringE2E.harness.py"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo RUN_LEGAL_PROACTIVE_SPARRING_E2E: FAIL exit %ERR%
  exit /b %ERR%
)
echo RUN_LEGAL_PROACTIVE_SPARRING_E2E: ALL PASS
exit /b 0
