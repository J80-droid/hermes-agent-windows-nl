@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\repair_gateway_home.ps1" %*
exit /b %ERRORLEVEL%
