@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - Memory identity repair E2E

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_MEMORY_IDENTITY_REPAIR_E2E.ps1" %*
exit /b %ERRORLEVEL%
