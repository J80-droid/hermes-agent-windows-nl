@echo off
setlocal EnableExtensions
set "REPO_ROOT=%~dp0.."
cd /d "%REPO_ROOT%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\windows\scripts\run_lancedb_maintenance.ps1" %*
exit /b %ERRORLEVEL%
