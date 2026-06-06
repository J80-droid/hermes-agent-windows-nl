@echo off

setlocal

cd /d "%~dp0..\.."

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_PYTEST_UPSTREAM.ps1" %*

exit /b %ERRORLEVEL%
