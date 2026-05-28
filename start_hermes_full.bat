@echo off
rem Volledige launcher: SOUL, institutioneel, trust, Docker-check, dashboard (9119).
rem Zie windows\START.md en windows\launch_profiles.ps1
set "HERMES_LAUNCH_PROFILE=full"
call "%~dp0start_hermes.bat" %*
exit /b %ERRORLEVEL%
