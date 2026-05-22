@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "HERMES_WINDOWS_BAT_PARENT=1"
rem Dunne launcher: dubbelklik vanuit Explorer in scripts\windows\
rem Gebruik echte powershell.exe (omzeilt Windows Store "App execution alias").
set "PSX=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PSX%" set "PSX=powershell.exe"
pushd "%~dp0..\.."
if not exist "cli.py" (
  echo [ERROR] Geen hermes-agent repo hier ^(cli.py ontbreekt^). Huidige map:
  cd
  set "HERMES_WINDOWS_BAT_PARENT="
  popd
  pause
  exit /b 1
)
if not exist "%~dp0setup_hermes_windows.ps1" (
  echo [ERROR] setup_hermes_windows.ps1 niet gevonden naast deze .bat:
  echo   "%~dp0setup_hermes_windows.ps1"
  set "HERMES_WINDOWS_BAT_PARENT="
  popd
  pause
  exit /b 1
)
echo [Hermes] Start setup ^(repo: %CD%^)...
rem Batch-flags (--full-setup e.d.) NOOIT naar PS1: CMD-substitutie maakt daar -FULL-SETUP= van.
echo(%*| findstr /I "full-setup" >nul && set "HERMES_SETUP_FULL_SETUP=1"
echo(%*| findstr /I "files-only" >nul && set "HERMES_SETUP_FILES_ONLY=1"
echo(%*| findstr /I "quiet" >nul && set "HERMES_SETUP_QUIET=1"
"%PSX%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_hermes_windows.ps1"
set ERR=!ERRORLEVEL!
if !ERR! equ 0 set "HERMES_REPO=!CD!"
popd
if !ERR! neq 0 (
  echo.
  echo [ERROR] Setup stopte met code !ERR!
  set "HERMES_WINDOWS_BAT_PARENT="
  pause
  exit /b !ERR!
)
if defined HERMES_SETUP_SILENT (
  set "HERMES_WINDOWS_BAT_PARENT="
  exit /b 0
)
if /I "%~1"=="--quiet" (
  set "HERMES_WINDOWS_BAT_PARENT="
  exit /b 0
)
if defined HERMES_SETUP_FULL_SETUP (
  echo.
  echo [Hermes] Volledige configuratiewizard ^(OPEN_SETUP.bat — zelfde Python als launch_hermes^)...
  call "%~dp0OPEN_SETUP.bat"
  set "WIZ=!ERRORLEVEL!"
  if !WIZ! neq 0 (
    set "HERMES_WINDOWS_BAT_PARENT="
    pause
    exit /b !WIZ!
  )
)
set "HERMES_WINDOWS_BAT_PARENT="
echo.
if defined HERMES_REPO (
  echo [OK] Setup klaar. Hermes staat in: !HERMES_REPO!
) else (
  echo [OK] Setup klaar.
)
echo Dubbelklik Hermes_met_logo.bat in de windows\ map om Hermes te starten.
echo Open een nieuw cmd/powershell-venster en typ 'hermes' om te beginnen.
echo.
if not defined HERMES_SETUP_SILENT pause