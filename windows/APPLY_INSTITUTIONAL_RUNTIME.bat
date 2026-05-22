@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - institutioneel runtime (display + SOUL + E2E)

set "ESC= "
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
echo %ESC%[96m====================================================
echo  Hermes: institutioneel runtime (automatisch)
echo  - display alle profielen
echo  - SOUL Interaction + Outputformaat
echo  - RUN_INSTITUTIONAL_E2E
echo ====================================================%ESC%[0m
echo.

if /I "%~1"=="-NoE2E" set HERMES_SKIP_E2E=1
if /I "%~1"=="-NoPause" set HERMES_SKIP_PAUSE=1

set "PS_ARGS="
if defined HERMES_SKIP_E2E set "PS_ARGS=-SkipE2E"
if defined HERMES_SKIP_PAUSE set "PS_ARGS=%PS_ARGS% -NoPause"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_institutional_runtime.ps1" %PS_ARGS%
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (
  echo [ERROR] Exit %ERR%
  if not "%HERMES_SKIP_PAUSE%"=="1" pause
  exit /b %ERR%
)
if not "%HERMES_SKIP_PAUSE%"=="1" pause
exit /b 0
