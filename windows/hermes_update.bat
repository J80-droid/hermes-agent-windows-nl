@echo off
setlocal
cd /d "%~dp0.."
if not exist "%~dp0launch_hermes.bat" (
  echo [ERROR] launch_hermes.bat ontbreekt in windows\
  pause
  exit /b 1
)
call "%~dp0launch_hermes.bat" update %*
exit /b %ERRORLEVEL%
