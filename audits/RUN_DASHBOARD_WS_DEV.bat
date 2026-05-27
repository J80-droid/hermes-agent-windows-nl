@echo off
REM Alleen dashboard + browser (zelfde logica als start_hermes.bat).
setlocal
cd /d "%~dp0.."
rem Geen automatische browser-tab (zelfde als start_hermes.bat)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\windows\scripts\launch_dashboard_on_start.ps1" -RepoRoot "%CD%"
exit /b %ERRORLEVEL%
