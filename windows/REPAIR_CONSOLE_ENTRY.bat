@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo ====================================================
echo  Hermes: console-entry + gateway.cmd repair
echo ====================================================
echo [INFO] pip install -e .  ^(hermes -^> hermes_cli_entry^)
echo [INFO] gateway.cmd vernieuwen via overlay-bootstrap
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\repair_console_entry.ps1" %*
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo.
  echo [ERROR] REPAIR_CONSOLE_ENTRY exit %ERR%
  pause
  exit /b %ERR%
)
echo.
pause
exit /b 0
