@echo off

setlocal

cd /d "%~dp0..\.."

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_PRODUCTION_GATE.ps1" %*

exit /b %ERRORLEVEL%
