@echo off
cd /d "%~dp0\..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync_legal_soul_from_template.ps1"
exit /b %ERRORLEVEL%
