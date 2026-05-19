@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "HERMES_WINDOWS_BAT_PARENT=1"
set "PSX=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PSX%" set "PSX=powershell.exe"
cd /d "%~dp0.."
if not exist "cli.py" (
  echo [ERROR] Geen repo-root: cli.py ontbreekt na cd naar:
  cd
  pause
  exit /b 1
)
if not exist "%~dp0..\scripts\windows\setup_hermes_windows.ps1" (
  echo [ERROR] Kan setup-script niet vinden:
  echo   "%~dp0..\scripts\windows\setup_hermes_windows.ps1"
  pause
  exit /b 1
)
echo [Hermes] Start setup ^(repo: %CD%^)...
set "PSARGS=%*"
echo(%*| findstr /I "full-setup" >nul && set "HERMES_SETUP_FULL_SETUP=1"
if defined PSARGS (
  set "PSARGS=!PSARGS:--quiet=!"
  set "PSARGS=!PSARGS:--QUIET=!"
  set "PSARGS=!PSARGS:--full-setup=!"
  set "PSARGS=!PSARGS:--FULL-SETUP=!"
)
"%PSX%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\windows\setup_hermes_windows.ps1" !PSARGS!
set ERR=!ERRORLEVEL!
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
  set "HERMES_OPEN_SETUP_NOPAUSE=1"
  call "%~dp0OPEN_SETUP.bat"
  set "HERMES_OPEN_SETUP_NOPAUSE="
  set "WIZ=!ERRORLEVEL!"
  if !WIZ! neq 0 (
    set "HERMES_WINDOWS_BAT_PARENT="
    pause
    exit /b !WIZ!
  )
)
set "HERMES_WINDOWS_BAT_PARENT="
echo.
echo [OK] Setup klaar. Hermes opent in een nieuw venster ^(zelfde als de Desktop-snelkoppeling^).
echo Interactieve prompt hieronder voor aanpassingen ^(typ exit als klaar^).
echo.
if not defined HERMES_SETUP_NO_LAUNCH (
  if exist "windows\Hermes_met_logo.bat" (
    start "Hermes Agent" cmd /k "cd /d ""!CD!"" && call windows\Hermes_met_logo.bat"
  ) else if exist "windows\launch_hermes.bat" (
    start "Hermes Agent" cmd /k "cd /d ""!CD!"" && call windows\launch_hermes.bat"
  )
)
cmd /k "cd /d ""!CD!"" && title Hermes Agent repo && echo [Hermes] Repo-map: && cd && echo. && echo Voorbeelden:  notepad windows\launch_hermes.bat   explorer windows"
exit /b 0
