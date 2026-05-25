@echo off
setlocal
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "windows\audits\RUN_WINDOWS_PLATFORM_HARDENING_E2E.ps1" %*
exit /b %ERRORLEVEL%
