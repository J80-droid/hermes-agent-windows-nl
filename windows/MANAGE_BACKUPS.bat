@echo off
rem ANSI: cyan [96m] - anders dan start_hermes (goud) en UPDATE_HERMES (groen)
setlocal EnableExtensions
set "ESC= "
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
echo %ESC%[96m====================================================
echo  Hermes Agent: RUNNING SMART BACKUP
echo ====================================================%ESC%[0m
echo.
echo  Sluit Hermes/gateway volledig af vóór backup.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup_hermes.ps1"
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo.
  echo [ERROR] Backup mislukt of geblokkeerd ^(exit %ERR%^). Hermes nog actief?
  pause
  exit /b %ERR%
)
exit /b 0
