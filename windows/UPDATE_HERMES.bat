@echo off
REM UPDATE_HERMES.bat — upstream sync + post-merge (conda hermes-env).
REM -QuickFix: alleen repo-hygiene (quick_fix + guard); stopt als enige arg (geen upstream).
REM HERMES_WIN: pad naar windows\ (vast vóór shift; voorkomt %%~dp0-bug na -QuickFix).
REM HERMES_SKIP_PAUSE_AFTER_UPDATE=1: geen pause aan het einde (CI/automation).
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\.."
set "HERMES_WIN=%~dp0"
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
  powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_WIN%scripts\quick_fix_repo_hygiene.ps1" -RepoRoot "%CD%"
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
echo        Verify in de keten: .ps1 ^(geen pause^). Einde .bat: pause ^(overslaan: HERMES_SKIP_PAUSE_AFTER_UPDATE=1^).
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_WIN%upstream_sync.ps1" -Phase Update %*
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
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_WIN%fix_hermes_taskbar_pins.ps1" -RepoRoot "%CD%" -Quiet
if errorlevel 1 echo [WARN] fix_hermes_taskbar_pins.ps1 - draai handmatig FIX_TASKBAR_ICONS.bat
goto :team_display

:team_display
echo.
if exist "%HERMES_WIN%SKIP_TEAM_DISPLAY_AFTER_UPDATE" (
  echo [INFO] SKIP_TEAM_DISPLAY_AFTER_UPDATE - team display overgeslagen.
) else (
  echo [INFO] Team display-defaults toepassen...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_WIN%apply_team_display.ps1"
  if errorlevel 1 echo [WARN] apply_team_display.ps1 - controleer handmatig.
)

if "%HERMES_SKIP_PAUSE_AFTER_UPDATE%"=="1" goto :eof_no_pause
pause
:eof_no_pause
exit /b 0
