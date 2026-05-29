@echo off
REM UPDATE_HERMES.bat — upstream sync + post-merge (conda hermes-env).
REM -QuickFix: alleen repo-hygiene; stopt als enige arg (geen upstream).
REM Paden via pushd %%~dp0 (immuniteit voor HERMES_WIN / upstream_sync.ps1 env-vars).
REM HERMES_SKIP_PAUSE_AFTER_UPDATE=1: geen pause aan het einde.
setlocal EnableExtensions EnableDelayedExpansion

REM Wis vervuilde env-vars (voorkomt paden als repo"repo\windows\...)
set "UPSTREAM_SYNC_PS1="
set "HERMES_WIN="

if not exist "%~dp0upstream_sync.ps1" (
  echo [ERROR] Kan windows\UPDATE_HERMES.bat niet lokaliseren ^(upstream_sync.ps1 ontbreekt^).
  echo [INFO] Draai vanuit repo: windows\UPDATE_HERMES.bat
  echo [INFO] Taakbalk kapot? windows\FIX_TASKBAR_ICONS.bat
  pause
  exit /b 1
)
pushd "%~dp0"
set "HERMES_WIN=%CD%\"
set "SCRIPT_UPSTREAM=%CD%\upstream_sync.ps1"
popd
cd /d "%~dp0\.."
chcp 65001 >nul

set "ESC= "
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
echo %ESC%[92m====================================================
echo  Hermes Agent: UPDATE - conda hermes-env
echo ====================================================%ESC%[0m
echo.
echo [INFO] Keten in 3 fasen ^(windows\upstream_sync.ps1 -Phase Update^):
echo        1. Preflight     — git vs Nous upstream ^(ahead/behind, optioneel j/N^)
echo        2. hermes update — merge Nous + Python/npm + skills
echo        3. Post-merge    — trust + API/vault-env sync, toolsets, institutional runtime, RAG, verify, taakbalk
echo [INFO] Optioneel: -IncludeCodebaseSmoke ^(~32s^) of -IncludeCodebaseSmokeE2E ^(~45s E2E; geen E3^)
echo [INFO] Rommel in repo-root: -QuickFix ^(verplaatst untracked naar output/research/^)
echo.
if /I "%~1"=="-QuickFix" (
  echo [INFO] QuickFix repo-hygiene...
  if not exist "%~dp0scripts\quick_fix_repo_hygiene.ps1" (
    echo [ERROR] Ontbreekt: %~dp0scripts\quick_fix_repo_hygiene.ps1
    pause
    exit /b 1
  )
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\quick_fix_repo_hygiene.ps1" -RepoRoot "%CD%"
  if errorlevel 1 (
    echo [ERROR] QuickFix mislukt — los handmatig op of zie docs\WORKSPACE_CONVENTIONS.md
    pause
    exit /b 1
  )
  if "%~2"=="" (
    echo [OK] Alleen QuickFix — volledige update overgeslagen. Draai zonder -QuickFix voor upstream sync.
    if "%HERMES_SKIP_PAUSE_AFTER_UPDATE%"=="1" exit /b 0
    pause
    exit /b 0
  )
  shift
)
echo [INFO] Uitleg bij cijfers en vragen staat in het PowerShell-venster ^(grijs^).
echo        Bij ^>20 commits achter: typ **j** + Enter om door te gaan ^(of annuleer met N^).
echo        Zonder prompt: -Force of set HERMES_UPSTREAM_AUTO_CONFIRM=1
echo        Verify in de keten: .ps1 ^(geen pause^). Einde .bat: pause ^(overslaan: HERMES_SKIP_PAUSE_AFTER_UPDATE=1^).
echo.

if not exist "!SCRIPT_UPSTREAM!" (
  echo [ERROR] Ontbreekt: !SCRIPT_UPSTREAM!
  echo [INFO] Verwacht: windows\upstream_sync.ps1 naast dit bat-bestand.
  echo [INFO] Controleer user-env HERMES_WIN / UPSTREAM_SYNC_PS1 ^(moeten leeg of weg^).
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "!SCRIPT_UPSTREAM!" -Phase Update %*
set "ERR=!ERRORLEVEL!"
if not "!ERR!"=="0" (
  echo.
  echo [ERROR] Update keten gestopt met code !ERR! — zie rode regels hierboven.
  echo [INFO] Dirty repo? commit/stash. NativeCommandError conda? Zie windows\UPSTREAM_SYNC.md
  pause
  exit /b !ERR!
)

echo.
echo [OK] Update-keten geslaagd.
echo [INFO] Taakbalk-icoon UPDATE vernieuwen...
if exist "%~dp0fix_hermes_taskbar_pins.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_hermes_taskbar_pins.ps1" -RepoRoot "%CD%" -Quiet
  if errorlevel 1 echo [WARN] fix_hermes_taskbar_pins.ps1 - draai handmatig FIX_TASKBAR_ICONS.bat
) else (
  echo [WARN] fix_hermes_taskbar_pins.ps1 ontbreekt
)
goto :team_display

:team_display
echo.
if exist "!HERMES_WIN!SKIP_TEAM_DISPLAY_AFTER_UPDATE" (
  echo [INFO] SKIP_TEAM_DISPLAY_AFTER_UPDATE - team display overgeslagen.
) else (
  echo [INFO] Team display-defaults toepassen...
  if exist "%~dp0apply_team_display.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_team_display.ps1"
    if errorlevel 1 echo [WARN] apply_team_display.ps1 - controleer handmatig.
  ) else (
    echo [WARN] apply_team_display.ps1 ontbreekt
  )
)

if "%HERMES_SKIP_PAUSE_AFTER_UPDATE%"=="1" goto :eof_no_pause
pause
:eof_no_pause
exit /b 0
