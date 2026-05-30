@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\show_legal_ingest_dashboard.ps1" %*
exit /b %ERRORLEVEL%
