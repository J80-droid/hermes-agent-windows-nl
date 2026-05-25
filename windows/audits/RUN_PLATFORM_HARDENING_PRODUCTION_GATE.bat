@echo off
setlocal
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_PLATFORM_HARDENING_PRODUCTION_GATE.ps1" %*
exit /b %ERRORLEVEL%
