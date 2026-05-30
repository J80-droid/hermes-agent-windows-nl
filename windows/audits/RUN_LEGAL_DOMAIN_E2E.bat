@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - Legal domain E2E

if not defined HERMES_REPO_ROOT (
    for %%I in ("%~dp0..\..") do set "HERMES_REPO_ROOT=%%~fI"
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_LEGAL_DOMAIN_E2E.ps1" %*
exit /b %ERRORLEVEL%
