@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\windows\scripts\Invoke-LegalProactiveSparringE2E.ps1" -Context Manual
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo RUN_LEGAL_PROACTIVE_SPARRING_E2E: FAIL exit %ERR%
  exit /b %ERR%
)
echo RUN_LEGAL_PROACTIVE_SPARRING_E2E: ALL PASS
exit /b 0
