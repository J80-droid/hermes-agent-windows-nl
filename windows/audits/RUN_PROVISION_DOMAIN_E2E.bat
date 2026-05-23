@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
chcp 65001 >nul
title Hermes - Provision domain E2E

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_PROVISION_DOMAIN_E2E.ps1" %*
if errorlevel 1 exit /b 1
if not "%HERMES_SKIP_PAUSE%"=="1" pause
exit /b 0
