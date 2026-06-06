@echo off
rem Alias: dashboard + Codebase Viz. Zie windows\HERMES_ONDERHOUD.bat -DashboardOnly
cd /d "%~dp0.."
call "%~dp0..\windows\HERMES_ONDERHOUD.bat" -DashboardOnly %*
exit /b %ERRORLEVEL%
