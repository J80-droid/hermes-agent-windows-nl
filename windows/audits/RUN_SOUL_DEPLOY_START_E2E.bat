@echo off
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_SOUL_DEPLOY_START_E2E.ps1" %*
exit /b %ERRORLEVEL%
