@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul

set "ESC= "
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
echo %ESC%[96m====================================================
echo  Hermes: team display-defaults (apply_team_display.ps1)
echo ====================================================%ESC%[0m

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_team_display.ps1"
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (
  echo [ERROR] Exit %ERR%
  pause
  exit /b %ERR%
)
pause
exit /b 0
