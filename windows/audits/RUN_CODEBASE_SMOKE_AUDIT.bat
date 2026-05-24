@echo off
cd /d "%~dp0\..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_CODEBASE_SMOKE_AUDIT.ps1" %*
exit /b %ERRORLEVEL%
