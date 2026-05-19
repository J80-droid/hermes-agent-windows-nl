@echo off
setlocal EnableExtensions
rem Altijd NousResearch upstream/main (niet alleen fork origin). Zie windows\UPSTREAM_SYNC.md
set "HERMES_UPDATE_FROM_UPSTREAM=1"
cd /d "%~dp0.."
if not exist "%~dp0launch_hermes.bat" (
  echo [ERROR] launch_hermes.bat ontbreekt in windows\
  pause
  exit /b 1
)
call "%~dp0launch_hermes.bat" update %*
exit /b %ERRORLEVEL%
