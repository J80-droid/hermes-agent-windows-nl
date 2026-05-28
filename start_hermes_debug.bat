@echo off
rem Debug-start: sneller (geen dashboard), venster blijft open bij fout, logs zichtbaar.
setlocal EnableExtensions
cd /d "%~dp0"
set "HERMES_DEBUG_LAUNCH=1"
set "HERMES_SKIP_DASHBOARD_ON_START=1"
echo [DEBUG] Hermes debug launch — logs:
echo   %~dp0hermes_runtime.log
echo   %~dp0hermes_launch.log
echo   %~dp0hermes_last_error.log
echo.
call "%~dp0start_hermes.bat" %*
set "RC=%ERRORLEVEL%"
if %RC% neq 0 (
    echo.
    echo [DEBUG] Exit code %RC%. Zie logs hierboven.
    pause
) else (
    echo.
    echo [DEBUG] Chat beeindigd. Sluit dit venster of start opnieuw via start_hermes.bat.
)
exit /b %RC%
