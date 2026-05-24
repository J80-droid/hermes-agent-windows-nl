@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\inventory_hermes_home.ps1" %*
exit /b %ERRORLEVEL%
