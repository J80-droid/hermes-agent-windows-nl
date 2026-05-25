@echo off
setlocal
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "windows\audits\RUN_MEMORY_TRUST_INTEGRATION_E2E.ps1" %*
exit /b %ERRORLEVEL%
