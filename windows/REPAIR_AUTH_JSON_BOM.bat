@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo ====================================================
echo  Hermes: auth.json UTF-8 BOM repair (root + profielen)
echo ====================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\repair_auth_json_bom.ps1" -RepoRoot "%CD%"
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo [ERROR] Exit %ERR%
  pause
  exit /b %ERR%
)
echo.
echo Optioneel: hermes doctor --fix (zelfde repair via doctor)
pause
exit /b 0
