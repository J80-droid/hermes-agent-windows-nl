@echo off
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_CONTEXT_AWARE_PSEUDO_TABLE_E2E.ps1" %*
exit /b %ERRORLEVEL%
