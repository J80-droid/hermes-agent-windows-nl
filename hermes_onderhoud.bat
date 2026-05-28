@echo off
rem Dunne launcher: alles-in-één onderhoud na codewijzigingen
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "%~dp0windows\HERMES_ONDERHOUD.bat" (
  echo [ERROR] windows\HERMES_ONDERHOUD.bat ontbreekt.
  pause
  exit /b 1
)
call "%~dp0windows\HERMES_ONDERHOUD.bat" %*
exit /b %ERRORLEVEL%
