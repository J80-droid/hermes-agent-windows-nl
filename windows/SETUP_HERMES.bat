@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\.."
if not exist "cli.py" (
  echo [ERROR] Geen repo-root: cli.py ontbreekt.
  pause
  exit /b 1
)
chcp 65001 >nul

rem ANSI: cyaan — hoofd-setup (bestanden + optioneel wizard)
set "ESC= "
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
echo %ESC%[96m====================================================
echo  Hermes Agent: SETUP (bestanden + configuratiewizard)
echo ====================================================%ESC%[0m
echo [INFO] Repo-root: %CD%
echo [INFO] Alleen bestanden/pip:  SETUP_HERMES.bat --files-only
echo [INFO] Stil ^(geen wizard^):   SETUP_HERMES.bat --quiet
echo.

set "USER_ARGS=%*"
set "RUN_ARGS=%USER_ARGS%"
echo(%USER_ARGS%| findstr /I "files-only" >nul && set "HERMES_SETUP_FILES_ONLY=1"
echo(%USER_ARGS%| findstr /I "quiet" >nul && set "HERMES_SETUP_QUIET=1"
if not defined HERMES_SETUP_FILES_ONLY if not defined HERMES_SETUP_QUIET (
  echo(!USER_ARGS!| findstr /I "full-setup" >nul || set "RUN_ARGS=--full-setup !USER_ARGS!"
)

if exist "%~dp0setup_hermes_windows.bat" (
  call "%~dp0setup_hermes_windows.bat" !RUN_ARGS!
  exit /b !ERRORLEVEL!
)

rem Eerste run: setup_hermes_windows.bat bestaat nog niet — zelfde keten als template
set "HERMES_WINDOWS_BAT_PARENT=1"
set "PSX=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PSX%" set "PSX=powershell.exe"
set "SETUP_PS1=%~dp0../scripts/windows/setup_hermes_windows.ps1"
if not exist "%SETUP_PS1%" set "SETUP_PS1=%~dp0setup_hermes_windows.ps1"
if not exist "%SETUP_PS1%" (
  echo [ERROR] setup_hermes_windows.ps1 niet gevonden.
  pause
  exit /b 1
)
echo [Hermes] Start setup ^(repo: %CD%^)...
echo(!RUN_ARGS!| findstr /I "full-setup" >nul && set "HERMES_SETUP_FULL_SETUP=1"
rem Batch-flags nooit naar PS1 doorgeven (zie setup_hermes_windows.bat).
"%PSX%" -NoProfile -ExecutionPolicy Bypass -File "%SETUP_PS1%"
set ERR=!ERRORLEVEL!
if !ERR! neq 0 (
  echo [ERROR] Setup stopte met code !ERR!
  pause
  exit /b !ERR!
)
if defined HERMES_SETUP_QUIET exit /b 0
if defined HERMES_SETUP_FILES_ONLY (
  echo [OK] Bestanden-setup klaar ^(geen wizard^). Wizard: OPEN_SETUP.bat
  pause
  exit /b 0
)
if defined HERMES_SETUP_FULL_SETUP (
  echo.
  echo [Hermes] Configuratiewizard ^(OPEN_SETUP.bat^)...
  set "HERMES_OPEN_SETUP_NOPAUSE=1"
  if exist "%~dp0..\scripts\windows\OPEN_SETUP.bat" (
    call "%~dp0..\scripts\windows\OPEN_SETUP.bat"
  ) else (
    call "%~dp0OPEN_SETUP.bat"
  )
  set "WIZ=!ERRORLEVEL!"
  if !WIZ! neq 0 (
    pause
    exit /b !WIZ!
  )
)
echo [OK] Setup klaar. Wizard: windows\OPEN_SETUP.bat
pause
exit /b 0
