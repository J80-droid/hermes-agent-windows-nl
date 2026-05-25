@echo off
setlocal
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "windows\audits\RUN_PLATFORM_HARDENING_REGRESSION_E2E.ps1" %*
exit /b %ERRORLEVEL%
