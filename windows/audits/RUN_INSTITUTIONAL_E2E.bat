@echo off
cd /d "%~dp0\.."
set "PS_ARGS="
if /I "%~1"=="-ApplyRuntime" set "PS_ARGS=-ApplyRuntime"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_INSTITUTIONAL_E2E.ps1" %PS_ARGS%
exit /b %ERRORLEVEL%
