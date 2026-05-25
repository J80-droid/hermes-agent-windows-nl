@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_INSTITUTIONAL_PRODUCTION_GATE.ps1" %*
exit /b %ERRORLEVEL%
