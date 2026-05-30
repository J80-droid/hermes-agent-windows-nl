@echo off
REM Zelfde keten als UPDATE_HERMES.bat, maar zonder j/N-vraag bij grote achterstand (handig voor taakbalk/automation).
setlocal EnableExtensions
set "HERMES_UPSTREAM_AUTO_CONFIRM=1"
set "HERMES_SKIP_PAUSE_AFTER_UPDATE=1"
call "%~dp0UPDATE_HERMES.bat" %*
exit /b %ERRORLEVEL%
