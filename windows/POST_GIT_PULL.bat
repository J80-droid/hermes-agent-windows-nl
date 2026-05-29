@echo off
REM Na git pull: verify, trust/SOUL/drift, institutional runtime, optioneel RAG/smoke.
REM Standaard Hermes-relaunch via Invoke-HermesPostPullRelaunch.ps1 (-SkipRelaunch om uit te zetten).
REM -Full = -AutoRepairModelProvider + -IncludeInstitutionalVerify + relaunch.
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\.."
chcp 65001 >nul

set "HERMES_CODEBASE_SMOKE_MODE=none"
set "HERMES_AUTO_REPAIR_MODEL=0"
set "HERMES_POST_PULL_QUICKFIX=0"
set "HERMES_RELAUNCH=1"
set "HERMES_INCLUDE_RAG_PIPELINE=0"
set "HERMES_INCLUDE_INST_VERIFY=0"
set "HERMES_WIN=%~dp0"
if "%HERMES_SKIP_RELAUNCH_AFTER_PULL%"=="1" set "HERMES_RELAUNCH=0"
:parse_post_pull_args
if /I "%~1"=="-AutoRepairModelProvider" (
  set "HERMES_AUTO_REPAIR_MODEL=1"
  shift
  goto parse_post_pull_args
)
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
if /I "%~1"=="-QuickFix" (
  set "HERMES_POST_PULL_QUICKFIX=1"
  shift
  goto parse_post_pull_args
)
if /I "%~1"=="-SkipRelaunch" (
  set "HERMES_RELAUNCH=0"
  shift
  goto parse_post_pull_args
)
if /I "%~1"=="-RelaunchHermes" (
  set "HERMES_RELAUNCH=1"
  shift
  goto parse_post_pull_args
)
if /I "%~1"=="-IncludeRagPipeline" (
  set "HERMES_INCLUDE_RAG_PIPELINE=1"
  set "HERMES_RAG_ON_POST_PULL=1"
  shift
  goto parse_post_pull_args
)
if /I "%~1"=="-IncludeInstitutionalVerify" (
  set "HERMES_INCLUDE_INST_VERIFY=1"
  shift
  goto parse_post_pull_args
)
if /I "%~1"=="-Full" (
  set "HERMES_AUTO_REPAIR_MODEL=1"
  set "HERMES_INCLUDE_INST_VERIFY=1"
  set "HERMES_RELAUNCH=1"
  shift
  goto parse_post_pull_args
)
if not "%~1"=="" (
  echo [WARN] Onbekende optie: %~1
  shift
  goto parse_post_pull_args
)

echo ====================================================
echo  Hermes: na git pull (verify + sync + relaunch)
echo ====================================================
echo [INFO] Repo: %CD%
if exist "%CD%\.git\MERGE_HEAD" (
  echo [ERROR] Git merge niet afgerond — los conflicten op vóór POST_GIT_PULL.
  pause
  exit /b 5
)
if /I "!HERMES_RELAUNCH!"=="1" (
  echo [INFO] Na sync: Hermes herstart in WT ^(-SkipRelaunch om over te slaan^).
) else (
  echo [INFO] Relaunch uit ^(-SkipRelaunch of HERMES_SKIP_RELAUNCH_AFTER_PULL=1^).
)
if /I "!HERMES_CODEBASE_SMOKE_MODE!"=="e2e" (
  echo [INFO] Optie: -IncludeCodebaseSmokeE2E ^(~45s, E2E-poort^)
) else if /I "!HERMES_CODEBASE_SMOKE_MODE!"=="smoke" (
  echo [INFO] Optie: -IncludeCodebaseSmoke ^(~32s, snelle smoke^)
) else (
  echo [INFO] Optioneel: -IncludeCodebaseSmoke / -IncludeCodebaseSmokeE2E
)
if "!HERMES_AUTO_REPAIR_MODEL!"=="1" (
  echo [INFO] Optie: -AutoRepairModelProvider
)
if "!HERMES_INCLUDE_INST_VERIFY!"=="1" (
  echo [INFO] Optie: -IncludeInstitutionalVerify
)
if "!HERMES_INCLUDE_RAG_PIPELINE!"=="1" (
  echo [INFO] Optie: -IncludeRagPipeline ^(lang; alleen als bronnen aanwezig^)
)
echo [INFO] Preset: -Full = AutoRepair + InstitutionalVerify + Relaunch
echo.

set "POST_PULL_ERR=0"
set "SOUL_DEPLOY_OK=0"

if "!HERMES_POST_PULL_QUICKFIX!"=="1" (
  echo [INFO] QuickFix repo-hygiene ^(voor verify^)...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_WIN%scripts\quick_fix_repo_hygiene.ps1" -RepoRoot "%CD%" -NonInteractive
  if errorlevel 1 (
    echo [ERROR] QuickFix mislukt — zie docs\WORKSPACE_CONVENTIONS.md
    set "POST_PULL_ERR=1"
  ) else (
    echo [OK] QuickFix klaar.
  )
  echo.
)

echo [INFO] Windows script-keten verify ^(conditioneel, vóór trust^)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_WIN%scripts\HermesSessionMaintenance.ps1" -Phase ConditionalWindowsChainVerify -RepoRoot "%CD%"
if errorlevel 1 (
  echo [ERROR] Windows script-keten verify gefaald
  set "POST_PULL_ERR=1"
) else (
  echo [OK] Windows script-keten OK of overgeslagen ^(stamp^).
)

echo.
echo [INFO] Trust and Forensic runtime (SOUL + memory, geen scrub)...
set "HERMES_SKIP_PAUSE=1"
set "TRUST_ERR=0"
call "%~dp0SYNC_TRUST_RUNTIME.bat"
set "TRUST_ERR=!ERRORLEVEL!"
set "HERMES_SKIP_PAUSE="
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_WIN%scripts\Invoke-PostGitPullTrustOutcome.ps1" -TrustExitCode !TRUST_ERR! -RepoRoot "%CD%"
if errorlevel 1 set "POST_PULL_ERR=1"
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
if "!HERMES_AUTO_REPAIR_MODEL!"=="1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify_hermes_config_drift.ps1" -Strict -AutoRepairModelProvider
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify_hermes_config_drift.ps1" -Strict
)
if errorlevel 1 (
  echo [ERROR] verify_hermes_config_drift gefaald
  set "POST_PULL_ERR=1"
) else (
  echo [OK] verify_hermes_config_drift OK.
)
set "HERMES_SKIP_PAUSE="
echo.
echo [INFO] SOUL anatomy deploy (14 profielen + snippets, stamp bijwerken)...
set "HERMES_SKIP_PAUSE=1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch_soul_anatomy_deploy.ps1" -RepoRoot "%CD%" -Force -Quiet
if errorlevel 1 (
  echo [WARN] SOUL anatomy deploy mislukt — probeer APPLY_SOUL_ANATOMY_RUNTIME.bat
) else (
  set "SOUL_DEPLOY_OK=1"
  echo [OK] SOUL anatomy deploy + stamp bijgewerkt.
)
set "HERMES_SKIP_PAUSE="
echo.
echo [INFO] Institutioneel runtime (display, snippets)...
set "HERMES_SKIP_PAUSE=1"
if "!SOUL_DEPLOY_OK!"=="1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_institutional_runtime.ps1" -SkipE2E -NoPause -SkipSoul
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_institutional_runtime.ps1" -SkipE2E -NoPause
)
if errorlevel 1 (
  echo [WARN] apply_institutional_runtime.ps1 mislukt — APPLY_INSTITUTIONAL_RUNTIME.bat
)
set "HERMES_SKIP_PAUSE="
if "!HERMES_INCLUDE_RAG_PIPELINE!"=="1" set "HERMES_RAG_ON_POST_PULL=1"
echo.
echo [INFO] Post-pull onderhoud ^(toolsets, TUI, pins, optioneel RAG^)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_WIN%scripts\Invoke-HermesPostPullMaintenance.ps1" -RepoRoot "%CD%" -Phase PostPullTail
if errorlevel 1 set "POST_PULL_ERR=1"

if /I "!HERMES_CODEBASE_SMOKE_MODE!"=="e2e" (
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Invoke-PostSyncCodebaseSmoke.ps1" -RepoRoot "%CD%" -Level E2E
  if errorlevel 1 set "POST_PULL_ERR=1"
) else if /I "!HERMES_CODEBASE_SMOKE_MODE!"=="smoke" (
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Invoke-PostSyncCodebaseSmoke.ps1" -RepoRoot "%CD%" -Level Smoke
  if errorlevel 1 set "POST_PULL_ERR=1"
)

if "!HERMES_INCLUDE_INST_VERIFY!"=="1" (
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_WIN%scripts\Invoke-PostGitPullInstitutionalVerify.ps1" -RepoRoot "%CD%"
  if errorlevel 1 set "POST_PULL_ERR=1"
)

echo.
if not "!POST_PULL_ERR!"=="0" (
  echo [ERROR] POST_GIT_PULL afgerond met fouten ^(code !POST_PULL_ERR!^) — geen relaunch.
  pause
  exit /b !POST_PULL_ERR!
)

if /I "!HERMES_RELAUNCH!"=="1" (
  echo [INFO] Hermes relaunch ^(stop + WT-start^)...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $ErrorActionPreference='Stop'; & '%HERMES_WIN%scripts\Invoke-HermesPostPullRelaunch.ps1' -RepoRoot '%CD%' -KeepPid $PID; exit $LASTEXITCODE }"
  if errorlevel 1 (
    echo [WARN] Relaunch mislukt — start handmatig start_hermes.bat
    pause
    exit /b 1
  )
  goto :eof_no_pause
)

echo [INFO] Klaar. Start Hermes: start_hermes.bat
if /I not "!HERMES_CODEBASE_SMOKE_MODE!"=="none" goto :eof_no_pause
if "%HERMES_SKIP_PAUSE%"=="1" goto :eof_no_pause
pause
:eof_no_pause
exit /b 0
