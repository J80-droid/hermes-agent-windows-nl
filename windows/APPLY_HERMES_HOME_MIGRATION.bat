@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - split-home migratie (backup + deprecate + preset + E2E)

set "ESC= "
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
echo %ESC%[96m====================================================
echo  Hermes: split-home migratie (automatisch)
echo  - backup (MANAGE_BACKUPS)
echo  - deprecate legacy ~/.hermes/config.yaml
echo  - merge legacy providers (Venice)
echo  - auxiliary hybrid preset + strip profile blocks
echo  - sync API env (legacy -^> runtime)
echo  - RUN_HERMES_HOME_E2E
echo ====================================================%ESC%[0m
echo.
echo  Sluit Hermes/gateway volledig af vóór start.
echo  Her-run zonder backup: APPLY_HERMES_HOME_MIGRATION.bat -SkipBackup -NoPause
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_hermes_home_migration.ps1" %*
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (
  echo [ERROR] Migratie mislukt ^(exit %ERR%^).
  pause
  exit /b %ERR%
)
exit /b 0
