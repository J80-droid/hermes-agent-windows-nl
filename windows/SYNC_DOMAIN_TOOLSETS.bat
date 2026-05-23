@echo off
rem platform_toolsets.cli per domein uit docs/domain_toolsets.yaml
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - Domein toolsets sync

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_profile_toolsets_from_manifest.ps1" %*
if errorlevel 1 exit /b 1

echo.
echo [OK] Domein-toolsets gesynchroniseerd. Nieuwe chat per profiel voor actieve toolbox.
echo   Ontbrekend profiel? windows\SYNC_DOMAIN_TOOLSETS.bat --create-missing
if not "%HERMES_SKIP_PAUSE%"=="1" pause
exit /b 0
