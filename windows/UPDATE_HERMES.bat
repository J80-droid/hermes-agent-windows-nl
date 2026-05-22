@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\.."
chcp 65001 >nul

set "ESC= "
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
echo %ESC%[92m====================================================
echo  Hermes Agent: UPDATE - conda hermes-env
echo ====================================================%ESC%[0m
echo.
echo [INFO] Volledige keten: preflight + hermes update + post-merge
echo        ^(windows\upstream_sync.ps1 -Phase Update^)
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0upstream_sync.ps1" -Phase Update %*
set "ERR=!ERRORLEVEL!"
if not "!ERR!"=="0" (
  echo.
  echo [ERROR] Update keten gestopt met code !ERR! — zie rode regels hierboven.
  echo [INFO] Dirty repo? commit/stash. NativeCommandError conda? Zie windows\UPSTREAM_SYNC.md
  pause
  exit /b !ERR!
)

echo.
echo [OK] Update-keten geslaagd.
echo [INFO] Taakbalk-icoon UPDATE vernieuwen...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_hermes_taskbar_pins.ps1" -RepoRoot "%CD%" -Quiet
if errorlevel 1 echo [WARN] fix_hermes_taskbar_pins.ps1 - draai handmatig FIX_TASKBAR_ICONS.bat
goto :team_display

:team_display
echo.
if exist "%~dp0SKIP_TEAM_DISPLAY_AFTER_UPDATE" (
  echo [INFO] SKIP_TEAM_DISPLAY_AFTER_UPDATE - team display overgeslagen.
) else (
  echo [INFO] Team display-defaults toepassen...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_team_display.ps1"
  if errorlevel 1 echo [WARN] apply_team_display.ps1 - controleer handmatig.
)

pause
exit /b 0
