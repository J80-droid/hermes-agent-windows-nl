@echo off
rem SOUL + memory + limits — geen identiteit-scrub (veilig na git pull / dagelijks).
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - Trust runtime sync (geen scrub)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_legal_soul_from_template.ps1" %*
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_soul_anatomy_snippets.ps1" -Force %*
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_profile_memories.ps1" %*
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\invoke_deduplicate_memories.ps1" %*
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\apply_trust_memory_limits.ps1" %*
if errorlevel 1 exit /b 1
echo.
echo [INFO] API-keys + vault-paden (~/.hermes -^> alle profiel-.env)...
set "HERMES_SKIP_PAUSE=1"
call "%~dp0SYNC_HERMES_API_ENV.bat"
set "HERMES_SKIP_PAUSE="
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\log_trust_memory_user_snapshot.ps1" %*
if errorlevel 1 (
  echo.
  echo [FAIL] Trust memory snapshot mislukt.
  if not "%HERMES_SKIP_PAUSE%"=="1" pause
  exit /b 1
)

echo.
echo [INFO] Audit + productie-poort + /new-reminder...
set "HERMES_SKIP_PAUSE=1"
if "%HERMES_SKIP_MEMORY_PRODUCTION_GATE%"=="1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Invoke-MemoryTrustPostSync.ps1" -SkipProductionGate %*
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Invoke-MemoryTrustPostSync.ps1" %*
)
if errorlevel 1 (
  echo [FAIL] Memory/trust post-sync mislukt.
  if not "%HERMES_SKIP_PAUSE%"=="1" pause
  exit /b 1
)

echo.
echo [OK] Trust runtime volledig gesynchroniseerd. Open TUI: auto /new; anders banner bij start.
exit /b 0
