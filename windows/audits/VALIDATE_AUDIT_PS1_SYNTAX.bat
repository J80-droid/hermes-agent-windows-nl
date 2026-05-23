@echo off
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "windows\tests\Validate-AuditPs1Syntax.ps1"
exit /b %ERRORLEVEL%
