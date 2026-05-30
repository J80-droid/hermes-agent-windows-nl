@echo off
REM Snelle legal runtime verify (volledige poort: audits\RUN_LEGAL_DOMAIN_E2E.bat)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify_legal_runtime.ps1" %*
exit /b %ERRORLEVEL%
