@echo off
setlocal
set "HERMES_WIN=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_WIN%SYNC_NOUS_E2E.core.ps1"
exit /b %ERRORLEVEL%
