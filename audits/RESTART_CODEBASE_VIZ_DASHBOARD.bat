@echo off
rem Alias: dashboard + Codebase Viz onderhoud. Zie windows\HERMES_ONDERHOUD.bat.
cd /d "%~dp0.."
call "%~dp0..\windows\HERMES_ONDERHOUD.bat" -DashboardOnly %*
exit /b %ERRORLEVEL%
