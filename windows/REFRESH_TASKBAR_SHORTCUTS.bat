@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo ====================================================
echo  Hermes: taakbalk-snelkoppelingen in windows\
echo ====================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_taskbar_shortcuts.ps1" -RepoRoot "%CD%"
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo [ERROR] Exit %ERR%
  pause
  exit /b %ERR%
)
echo.
echo Snelkoppelingen staan in: %~dp0
echo.
echo Taakbalk vastzetten ^(Windows 11^):
echo   1. Sleep "Hermes - update - naar taakbalk slepen.lnk" naar Bureaublad
echo   2. Rechtsklik op de .lnk -^> "Vastmaken aan taakbalk"
echo   Of: sleep naar Start, dan rechtsklik -^> Vastmaken aan taakbalk
echo.
echo Werkt slepen direct naar taakbalk niet? Gebruik rechtsklik-pin ^(cmd.exe-wrapper^).
echo.
echo Zie je nog een zwart H-icoon? Draai: FIX_TASKBAR_ICONS.bat ^(vernieuwt ook vastgezette pins^).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_hermes_taskbar_pins.ps1" -RepoRoot "%CD%" -Quiet
pause
exit /b 0
