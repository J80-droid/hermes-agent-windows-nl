@echo off
cd /d "%~dp0\..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_ROOT_CONFIG_INHERITANCE_E2E.ps1" %*
exit /b %ERRORLEVEL%
