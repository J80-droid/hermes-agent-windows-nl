@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_PERFORMANCE_ARCHITECTURE_E2E.ps1" %*
exit /b %ERRORLEVEL%
