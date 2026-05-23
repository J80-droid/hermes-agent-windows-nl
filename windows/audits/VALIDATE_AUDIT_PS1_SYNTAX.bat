@echo off
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\tests\Validate-AuditPs1Syntax.ps1"
exit /b %ERRORLEVEL%
