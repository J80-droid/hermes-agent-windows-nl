@echo off
rem SOUL + memory + limits — geen identiteit-scrub (veilig na git pull / dagelijks).
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - Trust runtime sync (geen scrub)

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
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\log_trust_memory_user_snapshot.ps1" %*
if errorlevel 1 exit /b 1

echo.
echo [OK] Trust runtime gesynchroniseerd (geen scrub). Nieuwe chat starten.
if not "%HERMES_SKIP_PAUSE%"=="1" pause
exit /b 0
