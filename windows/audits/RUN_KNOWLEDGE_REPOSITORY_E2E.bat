@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_KNOWLEDGE_REPOSITORY_E2E.ps1" %*
exit /b %ERRORLEVEL%
