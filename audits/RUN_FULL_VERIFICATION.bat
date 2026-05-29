@echo off
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_FULL_VERIFICATION.ps1" %*
exit /b %ERRORLEVEL%
