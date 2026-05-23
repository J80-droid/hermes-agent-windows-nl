@echo off
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_STATUS_BAR_COST_E2E.ps1" %*
exit /b %ERRORLEVEL%
