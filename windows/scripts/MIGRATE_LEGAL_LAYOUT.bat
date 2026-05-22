@echo off
cd /d "%~dp0\..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0migrate_legal_source_layout.ps1" %*
if "%~1"=="-Apply" goto done
echo.
echo  Dry-run. Voor echte migratie:
echo    "%~nx0" -Apply
echo.
:done
pause
exit /b %ERRORLEVEL%
