@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify_gateway_home.ps1" %*
exit /b %ERRORLEVEL%
