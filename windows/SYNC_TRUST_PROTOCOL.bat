@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - Trust and Forensic protocol (volledig)

echo [INFO] Backup aanbevolen: MANAGE_BACKUPS.bat vóór scrub.
echo.

set "HERMES_SKIP_PAUSE=1"
echo [INFO] Pre-sync runtime identity scrub...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\repair_runtime_identity.ps1"
if errorlevel 1 exit /b 1

call "%~dp0SYNC_TRUST_RUNTIME.bat"
if errorlevel 1 exit /b 1

echo.
echo [INFO] Repo identity scrub (docs, windows, memory-bank)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\scrub_identity_to_J.ps1" -RepoOnly -IncludeRawSource %*
if errorlevel 1 exit /b 1

echo.
echo [OK] Trust protocol volledig. Bij bronwijzigingen: RAG_KNOWLEDGE_UPDATE.bat legal
exit /b 0
