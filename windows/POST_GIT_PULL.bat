@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\.."
chcp 65001 >nul

set "HERMES_CODEBASE_SMOKE_MODE=none"
:parse_post_pull_args
if /I "%~1"=="-IncludeCodebaseSmokeE2E" (
  set "HERMES_CODEBASE_SMOKE_MODE=e2e"
  shift
  goto parse_post_pull_args
)
if /I "%~1"=="-IncludeCodebaseSmoke" (
  if /I not "!HERMES_CODEBASE_SMOKE_MODE!"=="e2e" set "HERMES_CODEBASE_SMOKE_MODE=smoke"
  shift
  goto parse_post_pull_args
)
if not "%~1"=="" (
  echo [WARN] Onbekende optie: %~1
  shift
  goto parse_post_pull_args
)

echo ====================================================
echo  Hermes: na git pull (verify + taakbalk-iconen)
echo ====================================================
echo [INFO] Repo: %CD%
if /I "!HERMES_CODEBASE_SMOKE_MODE!"=="e2e" (
  echo [INFO] Optie: -IncludeCodebaseSmokeE2E ^(~45s, E2E-poort^)
) else if /I "!HERMES_CODEBASE_SMOKE_MODE!"=="smoke" (
  echo [INFO] Optie: -IncludeCodebaseSmoke ^(~32s, snelle smoke^)
) else (
  echo [INFO] Optioneel: -IncludeCodebaseSmoke ^(~32s^) of -IncludeCodebaseSmokeE2E ^(~45s^)
)
echo.

set "POST_PULL_ERR=0"

echo [INFO] Windows script-keten verify ^(geen pause^)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify_windows_script_chain.ps1"
if errorlevel 1 (
  echo [ERROR] verify_windows_script_chain.ps1 gefaald
  set "POST_PULL_ERR=1"
) else (
  echo [OK] Windows script-keten OK.
)

echo.
echo [INFO] Trust and Forensic runtime (SOUL + memory, geen scrub)...
set "HERMES_SKIP_PAUSE=1"
call "%~dp0SYNC_TRUST_RUNTIME.bat"
set "HERMES_SKIP_PAUSE="
echo.
echo [INFO] API-keys + Obsidian vault-paden (~/.hermes -^> alle profiel-.env)...
set "HERMES_SKIP_PAUSE=1"
call "%~dp0SYNC_HERMES_API_ENV.bat"
set "HERMES_SKIP_PAUSE="
echo.
echo [INFO] Hermes home + config drift verify...
set "HERMES_SKIP_PAUSE=1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify_hermes_home.ps1" -StrictDrift
if errorlevel 1 (
  echo [ERROR] verify_hermes_home / config drift gefaald
  set "POST_PULL_ERR=1"
) else (
  echo [OK] Hermes home + config drift OK.
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify_hermes_config_drift.ps1" -Strict
if errorlevel 1 (
  echo [ERROR] verify_hermes_config_drift gefaald
  set "POST_PULL_ERR=1"
) else (
  echo [OK] verify_hermes_config_drift OK.
)
set "HERMES_SKIP_PAUSE="
echo.
echo [INFO] SOUL anatomy deploy (13 profielen + snippets, stamp bijwerken)...
set "HERMES_SKIP_PAUSE=1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch_soul_anatomy_deploy.ps1" -RepoRoot "%CD%" -Force -Quiet
if errorlevel 1 (
  echo [WARN] SOUL anatomy deploy mislukt — probeer APPLY_SOUL_ANATOMY_RUNTIME.bat
) else (
  echo [OK] SOUL anatomy deploy + stamp bijgewerkt.
  echo [INFO] SOUL/snippets gewijzigd? Nieuwe chat: /new in TUI ^(reminder: institutional_new_chat_required.json^).
)
set "HERMES_SKIP_PAUSE="
echo.
echo [INFO] Domein-toolsets (platform_toolsets.cli)...
set "HERMES_SKIP_PAUSE=1"
call "%~dp0SYNC_DOMAIN_TOOLSETS.bat"
set "HERMES_SKIP_PAUSE="
echo.
echo [INFO] TUI bundel (ui-tui/dist) herbouwen indien bron nieuwer...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\rebuild_tui.ps1" -RepoRoot "%CD%"
if errorlevel 1 (
  echo [WARN] rebuild_tui.ps1 mislukt — sluit Hermes af en start opnieuw
) else (
  echo [OK] TUI dist gecontroleerd/herbouwd.
)
echo.
echo [INFO] Nieuwe skills (bijv. landkaart): hermes update of nieuwe chat-sessie.
echo.
echo [INFO] Taakbalk-.lnk en icooncache vernieuwen...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_hermes_taskbar_pins.ps1" -RepoRoot "%CD%" -Quiet
if errorlevel 1 (
  echo [WARN] fix_hermes_taskbar_pins.ps1 mislukt
) else (
  echo [OK] Taakbalk-snelkoppelingen bijgewerkt.
)

if /I "!HERMES_CODEBASE_SMOKE_MODE!"=="e2e" (
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Invoke-PostSyncCodebaseSmoke.ps1" -RepoRoot "%CD%" -Level E2E
  if errorlevel 1 set "POST_PULL_ERR=1"
) else if /I "!HERMES_CODEBASE_SMOKE_MODE!"=="smoke" (
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Invoke-PostSyncCodebaseSmoke.ps1" -RepoRoot "%CD%" -Level Smoke
  if errorlevel 1 set "POST_PULL_ERR=1"
)

echo.
echo [INFO] Eenmalig bij oud zwart H op UPDATE:
echo   1. Rechtsklik UPDATE-pin - Losmaken van de taakbalk
echo   2. windows\Hermes - update - naar taakbalk slepen.lnk - Vastmaken aan taakbalk
echo      (niet UPDATE_HERMES.bat direct slepen)
echo.
if not "!POST_PULL_ERR!"=="0" (
  echo.
  echo [ERROR] POST_GIT_PULL afgerond met fouten ^(code !POST_PULL_ERR!^).
  pause
  exit /b !POST_PULL_ERR!
)
if /I not "!HERMES_CODEBASE_SMOKE_MODE!"=="none" goto :eof_no_pause
if "%HERMES_SKIP_PAUSE%"=="1" goto :eof_no_pause
pause
:eof_no_pause
exit /b 0
