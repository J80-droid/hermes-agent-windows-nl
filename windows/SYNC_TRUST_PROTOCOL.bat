@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - Trust and Forensic protocol sync

echo [INFO] Backup aanbevolen: MANAGE_BACKUPS.bat vóór scrub.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_legal_soul_from_template.ps1" %*
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_soul_advisory_snippet.ps1" %*
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_soul_interaction_snippet.ps1" %*
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_soul_output_format_snippet.ps1" %*
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_profile_memories.ps1" %*
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\apply_trust_memory_limits.ps1" %*
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\scrub_identity_to_J.ps1" -IncludeRawSource %*
if errorlevel 1 exit /b 1

echo.
echo [OK] Trust protocol gesynchroniseerd. Start een nieuwe chat per profiel.
if not "%HERMES_SKIP_PAUSE%"=="1" pause
exit /b 0
