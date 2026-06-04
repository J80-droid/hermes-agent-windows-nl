@echo off
setlocal
set "HERMES_WIN=%~dp0"
if "%~1"=="" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_WIN%scripts\sync_nous.ps1" -Phase Full -RepoRoot "%~dp0.."
  exit /b %ERRORLEVEL%
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_WIN%scripts\sync_nous.ps1" %*
exit /b %ERRORLEVEL%
