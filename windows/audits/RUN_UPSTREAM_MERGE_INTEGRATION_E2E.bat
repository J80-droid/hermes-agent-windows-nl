@echo off
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_UPSTREAM_MERGE_INTEGRATION_E2E.ps1" %*
exit /b %ERRORLEVEL%
