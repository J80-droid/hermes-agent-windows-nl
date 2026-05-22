@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - sync SOUL Interaction snippet

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_soul_interaction_snippet.ps1" %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" exit /b %ERR%
echo.
echo [OK] Interaction-snippet gesynchroniseerd. Start een nieuwe chat voor effect.
pause
exit /b 0
