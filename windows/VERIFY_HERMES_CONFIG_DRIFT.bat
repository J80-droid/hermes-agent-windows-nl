@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify_hermes_config_drift.ps1" %*
exit /b %ERRORLEVEL%
