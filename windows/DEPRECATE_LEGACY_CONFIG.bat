@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\deprecate_legacy_config.ps1" %*
exit /b %ERRORLEVEL%
