@echo off
rem Controleer .bat-.ps1 ketens + kritieke backup-scripts in repo (institutioneel).
setlocal EnableExtensions
chcp 65001 >nul
title Hermes - verify Windows script chain

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify_windows_script_chain.ps1"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo [ERROR] Script-keten incompleet. Zie bovenstaande FAIL-regels.
  echo        Herstel: git pull  of  windows\restore_local_assets.bat
  pause
  exit /b %ERR%
)
echo.
echo [OK] Windows script-keten OK.
pause
exit /b 0
