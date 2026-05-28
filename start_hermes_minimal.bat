@echo off
rem Snelle start (geen SOUL/Docker/dashboard bij launch). Zie windows\START.md
set "HERMES_LAUNCH_PROFILE=minimal"
call "%~dp0start_hermes.bat" %*
exit /b %ERRORLEVEL%
