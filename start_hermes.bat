@echo off
rem Dunne launcher op repo-root: alle logica staat in windows\launch_hermes.bat
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "%~dp0windows\launch_hermes.bat" (
  echo [ERROR] windows\launch_hermes.bat ontbreekt. Herstel de map windows\ uit git of backup.
  pause
  exit /b 1
)
call "%~dp0windows\launch_hermes.bat" %*
exit /b %ERRORLEVEL%
