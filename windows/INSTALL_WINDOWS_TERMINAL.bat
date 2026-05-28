@echo off

setlocal EnableExtensions

cd /d "%~dp0.."

echo [INFO] Windows Terminal installeren (vereiste voor Hermes TUI)...

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_windows_terminal.ps1"

set "EC=%ERRORLEVEL%"

if %EC% neq 0 (

  echo [ERROR] Installatie mislukt. Zie windows\WINDOWS_REQUIREMENTS.md

  pause

  exit /b %EC%

)

echo [OK] Klaar. Start Hermes opnieuw via start_hermes.bat

pause

exit /b 0

