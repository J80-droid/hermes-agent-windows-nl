@echo off
setlocal EnableExtensions
rem Zelfde keten als UPDATE_HERMES.bat (preflight zit IN upstream_sync.ps1 -Phase Update)
cd /d "%~dp0.."
if not exist "%~dp0UPDATE_HERMES.bat" (
  echo [ERROR] UPDATE_HERMES.bat ontbreekt in windows\
  pause
  exit /b 1
)
call "%~dp0UPDATE_HERMES.bat" %*
exit /b %ERRORLEVEL%
