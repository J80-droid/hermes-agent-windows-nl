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
rem Forward slashes in paden: CMD met delayed expansion ziet \s in \setup als TAB (split pad -> error 9009).
set "SETUP_PS1=%~dp0../scripts/windows/setup_hermes_windows.ps1"
if not exist "%SETUP_PS1%" (
  echo [ERROR] Kan setup-script niet vinden:
  echo   "%SETUP_PS1%"
  pause
  exit /b 1
)
echo [Hermes] Start setup ^(repo: %CD%^)...
rem Batch-flags (--full-setup e.d.) NOOIT naar PS1: CMD-substitutie maakt daar -FULL-SETUP= van.
echo(%*| findstr /I "full-setup" >nul && set "HERMES_SETUP_FULL_SETUP=1"
echo(%*| findstr /I "files-only" >nul && set "HERMES_SETUP_FILES_ONLY=1"
echo(%*| findstr /I "quiet" >nul && set "HERMES_SETUP_QUIET=1"
"%PSX%" -NoProfile -ExecutionPolicy Bypass -File "%SETUP_PS1%"
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
  echo [Hermes] Volledige configuratiewizard ^(OPEN_SETUP.bat - zelfde Python als launch_hermes^)...
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
echo [OK] Setup klaar.
if not defined HERMES_SETUP_NO_LAUNCH (
  if exist "windows/Hermes_met_logo.bat" (
    start "Hermes Agent" cmd /k "cd /d ""!CD!"" && call windows/Hermes_met_logo.bat"
  ) else if exist "windows/launch_hermes.bat" (
    start "Hermes Agent" cmd /k "cd /d ""!CD!"" && call windows/launch_hermes.bat"
  )
)
echo [INFO] Dit venster blijft open. Typ exit om te sluiten, of gebruik het nieuwe Hermes-venster.
cmd /k "cd /d ""!CD!"" && title Hermes Agent repo"
exit /b 0

