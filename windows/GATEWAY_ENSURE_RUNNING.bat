@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0GATEWAY_ENSURE_RUNNING.ps1"
exit /b %ERRORLEVEL%
