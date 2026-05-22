@echo off

setlocal EnableExtensions

cd /d "%~dp0\.."

chcp 65001 >nul

if "%~1"=="" (

  echo.

  echo  Hermes: herstel repo vanuit een backupmap onder backups\

  echo.

  echo  Gebruik:

  echo    "%~nx0" "D:\pad\naar\hermes-agent\backups\backup_YYYY_MM_DD_HHMMSS"

  echo.

  echo  Optioneel ^(overschrijft %%USERPROFILE%%\.hermes — alleen disaster recovery^):

  echo    "%~nx0" "D:\...\backup_..." -RestoreUserProfile

  echo.

  echo  Alleen runtime-persona's ^(%%LOCALAPPDATA%%\hermes\profiles\*\SOUL.md etc.^):

  echo    "%~nx0" "D:\...\backup_..." -RestoreRuntimePersonas

  echo.

  exit /b 1

)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0restore_from_backup.ps1" -BackupPath "%~1" %2 %3 %4

set ERR=%ERRORLEVEL%

if %ERR% neq 0 (

  echo [ERROR] Exit %ERR%

  pause

  exit /b %ERR%

)

echo.

pause

exit /b 0

