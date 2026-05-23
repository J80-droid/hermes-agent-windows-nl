@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - migrate SOUL anatomy

if /I "%~1"=="-Apply" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\migrate_soul_anatomy.ps1" -Apply
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\migrate_soul_anatomy.ps1"
)
set ERR=%ERRORLEVEL%
if not "%HERMES_SKIP_PAUSE%"=="1" pause
exit /b %ERR%
