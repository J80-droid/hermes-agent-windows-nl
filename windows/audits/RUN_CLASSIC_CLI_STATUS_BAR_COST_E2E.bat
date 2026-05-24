@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1" %*
exit /b %ERRORLEVEL%
