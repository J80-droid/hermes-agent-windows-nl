@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - sync SOUL snippets (anatomy)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_soul_anatomy_snippets.ps1" %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" exit /b %ERR%
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_root_soul_fallback.ps1" -SnippetsOnly -Quiet
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" exit /b %ERR%

echo.
echo [OK] SOUL anatomy snippets gesynchroniseerd. Nieuwe chat starten (/new).
if not "%HERMES_SKIP_PAUSE%"=="1" pause
exit /b 0
