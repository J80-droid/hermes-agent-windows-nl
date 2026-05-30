@echo off
REM UPDATE_HERMES.bat — Eén keten: Nous upstream + deps + trust/RAG/verify (conda hermes-env).
REM   Normaal:       windows\UPDATE_HERMES.bat
REM   Grote merge:   windows\UPDATE_HERMES.bat -Yes  (geen j/N bij >20 commits achter)
REM   Alleen rommel: windows\UPDATE_HERMES.bat -QuickFix
REM   Zie: windows\UPSTREAM_SYNC.md  |  Snel zonder vraag: windows\UPDATE_HERMES_YES.bat
setlocal EnableExtensions EnableDelayedExpansion

set "UPSTREAM_SYNC_PS1="
set "HERMES_WIN="

if not exist "%~dp0upstream_sync.ps1" (
  echo [ERROR] Kan windows\UPDATE_HERMES.bat niet lokaliseren ^(upstream_sync.ps1 ontbreekt^).
  echo [INFO] Draai vanuit repo: windows\UPDATE_HERMES.bat
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
echo  Hermes Agent: UPDATE ^(Nous + fork^)
echo ====================================================%ESC%[0m
echo.
echo [INFO] Eén commando — 3 fasen: preflight ^(git^) - merge + deps - post-merge ^(trust/RAG^)
echo [INFO] Grote achterstand: typ j in PowerShell, of gebruik -Yes / UPDATE_HERMES_YES.bat
echo [INFO] Uitleg: windows\UPSTREAM_SYNC.md
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
    echo [ERROR] QuickFix mislukt — zie docs\WORKSPACE_CONVENTIONS.md
    pause
    exit /b 1
  )
  if "%~2"=="" (
    echo [OK] Alleen QuickFix — volledige update overgeslagen. Draai: windows\UPDATE_HERMES.bat
    if "%HERMES_SKIP_PAUSE_AFTER_UPDATE%"=="1" exit /b 0
    pause
    exit /b 0
  )
  shift
)

set "PS_ARGS="
set "FORCE_FLAG="
if "%HERMES_UPSTREAM_AUTO_CONFIRM%"=="1" set "FORCE_FLAG=-Force"

:parse_args
if "%~1"=="" goto :parse_done
if /I "%~1"=="-Yes" set "FORCE_FLAG=-Force" & shift & goto :parse_args
if /I "%~1"=="-y" set "FORCE_FLAG=-Force" & shift & goto :parse_args
set "PS_ARGS=!PS_ARGS! %~1"
shift
goto :parse_args

:parse_done
if defined FORCE_FLAG (
  echo [INFO] Automatisch doorgaan bij grote achterstand ^(-Yes / HERMES_UPSTREAM_AUTO_CONFIRM^).
  echo.
)

if not exist "!SCRIPT_UPSTREAM!" (
  echo [ERROR] Ontbreekt: !SCRIPT_UPSTREAM!
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "!SCRIPT_UPSTREAM!" -Phase Update !FORCE_FLAG! !PS_ARGS!
set "ERR=!ERRORLEVEL!"
if not "!ERR!"=="0" (
  echo.
  echo [ERROR] Update keten gestopt met code !ERR!
  call :print_update_help !ERR!
  pause
  exit /b !ERR!
)

echo.
echo [OK] Update-keten geslaagd.
echo [INFO] Hermes opnieuw: windows\start_hermes.bat  —  in chat: /new
echo [INFO] Taakbalk-icoon UPDATE vernieuwen...
if exist "%~dp0fix_hermes_taskbar_pins.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_hermes_taskbar_pins.ps1" -RepoRoot "%CD%" -Quiet
  if errorlevel 1 echo [WARN] Draai FIX_TASKBAR_ICONS.bat
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
  )
)

if "%HERMES_SKIP_PAUSE_AFTER_UPDATE%"=="1" goto :eof_no_pause
pause
:eof_no_pause
exit /b 0

:print_update_help
if "%~1"=="2" (
  echo [HELP] Werkmap niet schoon: git commit of stash, of: UPDATE_HERMES.bat -QuickFix
  exit /b 0
)
if "%~1"=="4" (
  echo [HELP] Geannuleerd — repo ongewijzigd. Zonder vraag: UPDATE_HERMES.bat -Yes
  exit /b 0
)
if "%~1"=="6" (
  echo [HELP] Merge-conflict: windows\MERGE_UPSTREAM.bat  —  daarna UPDATE opnieuw
  echo [HELP] NOOIT: git reset --hard upstream main
  exit /b 0
)
if "%~1"=="7" (
  echo [HELP] Merge al bezig: conflicten oplossen of git merge --abort
  echo [HELP] Daarna: MERGE_UPSTREAM.bat -FinalizeOnly
  exit /b 0
)
echo [HELP] Zie windows\UPSTREAM_SYNC.md
exit /b 0
