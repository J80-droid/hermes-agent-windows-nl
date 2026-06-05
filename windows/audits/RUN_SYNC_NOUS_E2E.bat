@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0SYNC_NOUS_E2E.core.ps1"
exit /b %ERRORLEVEL%
