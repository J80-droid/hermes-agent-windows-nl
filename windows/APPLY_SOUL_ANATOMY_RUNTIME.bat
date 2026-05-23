@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - SOUL anatomy runtime

set HERMES_SKIP_PAUSE=1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_all_domain_souls_from_templates.ps1" -UpdateDeployStamp
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" exit /b %ERR%

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0audits\RUN_SOUL_ANATOMY_E2E.ps1"
exit /b %ERRORLEVEL%
