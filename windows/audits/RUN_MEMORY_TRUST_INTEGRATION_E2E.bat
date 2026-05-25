@echo off
setlocal
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_MEMORY_TRUST_INTEGRATION_E2E.ps1" %*
exit /b %ERRORLEVEL%
