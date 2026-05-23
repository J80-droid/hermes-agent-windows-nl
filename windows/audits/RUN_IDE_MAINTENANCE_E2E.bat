@echo off
cd /d "%~dp0\.."
set "PS_ARGS="
if /I "%~1"=="-ApplyDisplayFix" set "PS_ARGS=-ApplyDisplayFix"
if /I "%~1"=="-IncludeInstitutional" set "PS_ARGS=-IncludeInstitutional"
if /I "%~1"=="-Full" set "PS_ARGS=-ApplyDisplayFix -IncludeInstitutional"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_IDE_MAINTENANCE_E2E.ps1" %PS_ARGS%
exit /b %ERRORLEVEL%
