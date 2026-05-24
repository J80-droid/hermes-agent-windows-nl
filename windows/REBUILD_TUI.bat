@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo ====================================================
echo  Hermes: TUI bundel herbouwen (ui-tui/dist)
echo ====================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\rebuild_tui.ps1" -RepoRoot "%CD%"
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo [ERROR] Exit %ERR%
  pause
  exit /b %ERR%
)
echo.
echo Sluit Hermes volledig af en start opnieuw.
pause
exit /b 0
