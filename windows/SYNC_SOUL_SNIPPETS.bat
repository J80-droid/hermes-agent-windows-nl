@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - sync SOUL snippets (Interaction + Outputformaat)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_soul_interaction_snippet.ps1" %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" exit /b %ERR%
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_soul_output_format_snippet.ps1" %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" exit /b %ERR%
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_soul_tool_governance_snippet.ps1" %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" exit /b %ERR%
echo.
echo [OK] Interaction + Outputformaat + Tool governance gesynchroniseerd. Nieuwe chat starten.
if not "%HERMES_SKIP_PAUSE%"=="1" pause
exit /b 0
