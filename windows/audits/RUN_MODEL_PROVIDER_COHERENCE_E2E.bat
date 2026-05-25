@echo off
setlocal
cd /d "%~dp0..\.."
call "%~dp0..\..\audits\RUN_MODEL_PROVIDER_COHERENCE_E2E.bat"
exit /b %ERRORLEVEL%
