@echo off
setlocal EnableExtensions
rem Wrapper-only: canonieke implementatie leeft in scripts\windows\OPEN_SETUP.bat
set "CANON=%~dp0..\scripts\windows\OPEN_SETUP.bat"
if not exist "%CANON%" (
  echo [ERROR] Canonieke OPEN_SETUP ontbreekt:
  echo   "%CANON%"
  if not defined HERMES_OPEN_SETUP_NOPAUSE pause
  exit /b 1
)
call "%CANON%" %*
exit /b %ERRORLEVEL%
