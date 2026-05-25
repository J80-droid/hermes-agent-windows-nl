@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_HERMES_SHELL_COMMON_E2E.ps1" %*
exit /b %ERRORLEVEL%
