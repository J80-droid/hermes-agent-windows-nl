@echo off
rem Kopieer actieve API-keys van ~/.hermes/.env naar root %LOCALAPPDATA%\hermes\.env
setlocal EnableExtensions
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync_hermes_api_env.ps1"
exit /b %ERRORLEVEL%
