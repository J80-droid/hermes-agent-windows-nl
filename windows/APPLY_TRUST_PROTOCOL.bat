@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - Trust and Forensic protocol (volledige keten)

echo === Trust & Forensic protocol ===
echo.

call "%~dp0SYNC_TRUST_PROTOCOL.bat"
if errorlevel 1 exit /b 1

echo.
echo === E2E audit ===
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0audits\RUN_TRUST_FORENSIC_E2E.ps1"
set "ERR=%ERRORLEVEL%"

echo.
if "%ERR%"=="0" (
  echo [OK] Trust protocol + audit voltooid.
) else (
  echo [WARN] Sync OK maar audit exit %ERR%
)
if not "%HERMES_SKIP_PAUSE%"=="1" pause
exit /b %ERR%
