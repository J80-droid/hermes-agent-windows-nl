@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\apply_auxiliary_hybrid_preset.ps1" %*
exit /b %ERRORLEVEL%
