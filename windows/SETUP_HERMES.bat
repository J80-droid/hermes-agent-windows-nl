@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul

rem ANSI: cyaan [96m] — setup vs UPDATE (groen) / DOCTOR (magenta)
set "ESC= "
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
echo %ESC%[96m====================================================
echo  Hermes Agent: SETUP (workspace — setup_hermes_windows.ps1)
echo ====================================================%ESC%[0m
echo [INFO] Repo-root: %CD%
echo [INFO] Optioneel als administrator voor espeak-ng / systeem-PATH.
echo [INFO] Argumenten doorsturen, bv. --full-setup --with-doctor --pip-only
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_hermes_windows.ps1" %*

set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (
  echo [ERROR] Setup eindigde met code %ERR% — zie hermes_setup.log in repo-root.
  pause
  exit /b %ERR%
)
echo [OK] Setup klaar.
pause
exit /b 0
