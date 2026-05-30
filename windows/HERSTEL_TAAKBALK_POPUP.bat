@echo off
REM Alias: zelfde taakbalk-herstel als na UPDATE_HERMES (met pause en volledige fix-output).
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo [INFO] Zelfde keten als na windows\UPDATE_HERMES.bat — taakbalk herstellen...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_hermes_taskbar_pins.ps1" -RepoRoot "%CD%" -PostUpdateGuidance -OpenStableFolder
if errorlevel 1 (
  echo [ERROR] fix_hermes_taskbar_pins mislukt
  pause
  exit /b 1
)
pause
exit /b 0
