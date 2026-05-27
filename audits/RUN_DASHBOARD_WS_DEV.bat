@echo off
REM Alleen dashboard + browser (zelfde logica als start_hermes.bat).
setlocal
cd /d "%~dp0.."
set "HERMES_DASHBOARD_OPEN_PATH=/codebase-viz"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\windows\scripts\launch_dashboard_on_start.ps1" -RepoRoot "%CD%"
exit /b %ERRORLEVEL%
