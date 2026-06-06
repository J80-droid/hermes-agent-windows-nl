@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0GATEWAY_INSTALL_LOGIN.ps1"
exit /b %ERRORLEVEL%
