@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_UPSTREAM_SYNC_PHASE2_E2E.ps1" %*
exit /b %ERRORLEVEL%
