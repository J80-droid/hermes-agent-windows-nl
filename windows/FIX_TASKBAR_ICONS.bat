@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo ====================================================
echo  Hermes: taakbalk-iconen repareren
echo ====================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify_taskbar_shortcut_icons.ps1" -RepoRoot "%CD%" -Quiet
if %ERRORLEVEL% equ 0 goto :fix
echo [INFO] .lnk wijkt af — iconen en pins worden bijgewerkt...
:fix
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_hermes_taskbar_pins.ps1" -RepoRoot "%CD%"
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo [ERROR] Exit %ERR%
  pause
  exit /b %ERR%
)
echo.
echo Klaar. Los de oude pin los en maak opnieuw vast als het icoon nog H is.
pause
exit /b 0
