@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo ====================================================
echo  Hermes: security pins (PyNaCl, setuptools, diskcache)
echo ====================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\repair_security_pins.ps1" -RepoRoot "%CD%"
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo [ERROR] Exit %ERR%
  pause
  exit /b %ERR%
)
echo.
echo Optioneel: hermes security audit
pause
exit /b 0
