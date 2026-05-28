@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Ouder van windows\ = repo-root (HERMES_DIR)
set "WIN_SCR=%~dp0"
set "SCRIPT_SELF=%~f0"
for %%I in ("%WIN_SCR%..") do set "REPO_ROOT=%%~fI"
set "HERMES_DIR=%REPO_ROOT%\"
cd /d "%REPO_ROOT%"

rem RAG: per-domein via profiles + domains.yaml (geen globale my_lancedb default).
if not defined HERMES_RAG_RAW_SOURCE set "HERMES_RAG_RAW_SOURCE=%USERPROFILE%\data\raw_source_files"

rem Optioneel (productie-gateway): weiger start bij auth/config split-brain.
rem set "HERMES_STRICT_CONFIG_COHERENCE=1"

rem Gateway / TUI-subprocessen: expliciet hermes-env python (voorkomt `python` = kapotte OS-installatie).
if not defined HERMES_CONDA_ENV set "HERMES_CONDA_ENV=hermes-env"
if not defined HERMES_PYTHON if exist "%USERPROFILE%\miniconda3\envs\!HERMES_CONDA_ENV!\python.exe" set "HERMES_PYTHON=%USERPROFILE%\miniconda3\envs\!HERMES_CONDA_ENV!\python.exe"
if not defined HERMES_PYTHON if exist "%USERPROFILE%\anaconda3\envs\!HERMES_CONDA_ENV!\python.exe" set "HERMES_PYTHON=%USERPROFILE%\anaconda3\envs\!HERMES_CONDA_ENV!\python.exe"
if not defined HERMES_PYTHON if exist "%LOCALAPPDATA%\miniconda3\envs\!HERMES_CONDA_ENV!\python.exe" set "HERMES_PYTHON=%LOCALAPPDATA%\miniconda3\envs\!HERMES_CONDA_ENV!\python.exe"
if not defined HERMES_PYTHON if exist "%LOCALAPPDATA%\anaconda3\envs\!HERMES_CONDA_ENV!\python.exe" set "HERMES_PYTHON=%LOCALAPPDATA%\anaconda3\envs\!HERMES_CONDA_ENV!\python.exe"
if not defined HERMES_PYTHON if exist "C:\ProgramData\miniconda3\envs\!HERMES_CONDA_ENV!\python.exe" set "HERMES_PYTHON=C:\ProgramData\miniconda3\envs\!HERMES_CONDA_ENV!\python.exe"
if not defined HERMES_PYTHON if exist "C:\ProgramData\anaconda3\envs\!HERMES_CONDA_ENV!\python.exe" set "HERMES_PYTHON=C:\ProgramData\anaconda3\envs\!HERMES_CONDA_ENV!\python.exe"
if defined HERMES_PYTHON set "HERMES_PYTHON_ENV=!HERMES_PYTHON!"

rem --- Forceer UTF-8 codering voor moderne weergave ---
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
rem Herstel kleurweergave: externe shells zetten soms NO_COLOR/TERM=dumb/FORCE_COLOR=0.
if defined NO_COLOR set "NO_COLOR="
if /I "%TERM%"=="dumb" set "TERM="
if /I "%FORCE_COLOR%"=="0" set "FORCE_COLOR=1"

rem --- Genereer ESC karakter voor kleuren ---
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
set "GOUD=%ESC%[93m"
set "CYAAN=%ESC%[96m"
set "GROEN=%ESC%[92m"
set "ROOD=%ESC%[91m"
set "RESET=%ESC%[0m"

if defined HERMES_PYTHON echo %CYAAN%[INFO] HERMES_PYTHON=!HERMES_PYTHON! ^(gateway / tool-subprocessen^)%RESET%

rem --- Args vroeg (nodig vóór WT-relaunch) ---
set "CLEAN_ARGS=%*"
if defined CLEAN_ARGS set "CLEAN_ARGS=!CLEAN_ARGS:--maximized=!"

rem --- TrueColor: Windows Terminal. Geen TERM=xterm (breekt prompt_toolkit Win32). ---
set "WT_EXE="
where wt.exe >nul 2>&1 && set "WT_EXE=wt.exe"
if not defined WT_EXE if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe" set "WT_EXE=%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe"
if not defined WT_EXE where wt >nul 2>&1 && set "WT_EXE=wt"
if defined HERMES_AUTO_WINDOWS_TERMINAL if not defined HERMES_SKIP_WINDOWS_TERMINAL if not defined WT_SESSION if defined WT_EXE (
    echo %CYAAN%[INFO] Start in Windows Terminal ^(TrueColor^)...%RESET%
    if defined CLEAN_ARGS (set "HERMES_WT_LAUNCH_ARGS=!CLEAN_ARGS!") else (set "HERMES_WT_LAUNCH_ARGS=")
    "%WT_EXE%" -M -d "%REPO_ROOT%" %SystemRoot%\System32\cmd.exe /k call "%WIN_SCR%hermes_wt_entry.cmd"
    exit /b 0
)
if defined HERMES_AUTO_WINDOWS_TERMINAL if not defined HERMES_SKIP_WINDOWS_TERMINAL if not defined WT_SESSION (
    echo %GOUD%[WARN] Windows Terminal ^(wt^) niet gevonden - kleuren afwijkend in cmd. Zie windows\TERMINAL_WINDOWS.md%RESET%
)

rem ====================================================
rem  Hermes Agent - Institutional Launcher (v1.5)
rem ====================================================
if /I not "!HERMES_MINIMAL_LAUNCH!"=="1" (
echo %GOUD%
echo  ====================================================
echo   HERMES AGENT - WINDOWS PREMIUM LAUNCHER
echo  ====================================================
echo %RESET%
)

set "LAUNCH_LOG=%REPO_ROOT%\hermes_launch.log"

rem --- Filter internal --maximized (CLEAN_ARGS al gezet vóór WT) ---
if defined HERMES_RELAUNCH_ARGS (
    if not defined CLEAN_ARGS set "CLEAN_ARGS=%HERMES_RELAUNCH_ARGS%"
    set "HERMES_RELAUNCH_ARGS="
)

rem Initialize Logging safely with Rotation (Max 1MB)
if exist "%LAUNCH_LOG%" (
    for %%I in ("%LAUNCH_LOG%") do if %%~zI geq 1048576 (
        echo [%DATE% %TIME%] --- LOG ROTATED - MAX SIZE REACHED --- > "%LAUNCH_LOG%"
    )
)
echo [%DATE% %TIME%] --- NEW LAUNCH SESSION --- >> "%LAUNCH_LOG%" 2>nul

rem 1. Recursive Loop Protection & Window Maximization (nooit van WT terug naar ComSpec)
if "%~1"=="--maximized" set "HERMES_MAX_FLAG=1"
if "!HERMES_MAX_FLAG!"=="1" goto :check_elevation
if defined WT_SESSION (
    set "HERMES_MAX_FLAG=1"
    goto :check_elevation
)

echo %GOUD%[WARN] Legacy cmd-maximize — kleuren afwijkend. Installeer Windows Terminal ^(wt^).%RESET%
echo %CYAAN%[INFO] Maximaliseren venster...%RESET%
start "" /max "%ComSpec%" /k pushd "%REPO_ROOT%" ^&^& set HERMES_MAX_FLAG=1 ^&^& call "%SCRIPT_SELF%" --maximized !CLEAN_ARGS!
exit /b

:check_elevation
rem 2. Admin alleen op verzoek (UAC opent legacy cmd -> verkeerde kleuren). Standaard: gewone user in WT.
net session >nul 2>&1
if %errorLevel% equ 0 goto :run_agent
if not defined HERMES_REQUIRE_ADMIN goto :run_agent
echo %CYAAN%[INFO] Admin gevraagd ^(HERMES_REQUIRE_ADMIN=1^)...%RESET%
echo [%DATE% %TIME%] Requesting elevation... >> "%LAUNCH_LOG%"
if defined WT_EXE (
    powershell -NoProfile -Command "Start-Process -FilePath '%WT_EXE%' -ArgumentList '-M','-d','%REPO_ROOT%','cmd','/k','call \"\"%SCRIPT_SELF%\"\" --maximized %CLEAN_ARGS%' -Verb RunAs -WorkingDirectory '%REPO_ROOT%'"
) else (
    powershell -NoProfile -Command "Start-Process -FilePath '%SCRIPT_SELF%' -ArgumentList '--maximized !CLEAN_ARGS!' -Verb RunAs -WindowStyle Maximized -WorkingDirectory '%REPO_ROOT%'"
)
if !errorLevel! neq 0 (
    echo [ERROR] Elevation request failed or was cancelled.
    pause
)
exit /b

:run_agent
shift
cd /d "%REPO_ROOT%"

rem Eerst venster + schone console (vóór alle echo) — voorkomt buffer-corruptie en muiscapture.
powershell -NoProfile -ExecutionPolicy Bypass -Command ". '%REPO_ROOT%\windows\HermesShellCommon.ps1'; Reset-HermesConsoleInputModes; Invoke-HermesDisableConsoleQuickEdit; if ($env:HERMES_SKIP_CONSOLE_MAXIMIZE -ne '1') { [void][Invoke-HermesExpandConsoleWindow] }; try { Clear-Host } catch { }; Reset-HermesConsoleInputModes" 2>nul
cls >nul 2>&1

if /I "!HERMES_MINIMAL_LAUNCH!"=="1" goto :launch_chat

net session >nul 2>&1
if %errorLevel% equ 0 (
    echo %CYAAN%[INFO] Environment: Administrator%RESET%
) else (
    echo %CYAAN%[INFO] Environment: gebruiker ^(aanbevolen voor TrueColor in WT^)%RESET%
)
echo %CYAAN%[INFO] Window State: Maximized%RESET%
echo %CYAAN%[INFO] Directory: %CD%%RESET%
echo ----------------------------------------------------

rem ==========================================
rem  Docker Auto-Start & Verification
rem ==========================================
if /I "!HERMES_SKIP_DOCKER_ON_START!"=="1" goto :docker_done
echo %CYAAN%[INFO] Checking Docker daemon status...%RESET%
docker info >nul 2>&1
if %errorLevel% equ 0 (
    echo %GROEN%[OK] Docker is already running.%RESET%
    goto :docker_done
)

echo [INFO] Docker is not running. Booting Docker Desktop...
echo [%DATE% %TIME%] Booting Docker Desktop... >> "%LAUNCH_LOG%"

if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
) else (
    echo [WARNING] Docker Desktop not found at standard location.
    goto :docker_done
)

echo [INFO] Waiting for Docker Engine to initialize (this takes ~10-30 seconds)...
set DOCKER_RETRY=0

:docker_poll
timeout /t 5 /nobreak >nul
docker info >nul 2>&1
if %errorLevel% equ 0 (
    echo %GROEN%[INFO] Docker is fully loaded and ready!%RESET%
    goto :docker_done
)
set /a DOCKER_RETRY+=1
if %DOCKER_RETRY% geq 12 (
    echo %GOUD%[WARNING] Docker takes too long to start. We are continuing anyway...%RESET%
    echo [%DATE% %TIME%] WARNING: Docker timeout >> "%LAUNCH_LOG%"
    goto :docker_done
)
goto :docker_poll

:docker_done
if /I not "!HERMES_SKIP_DOCKER_ON_START!"=="1" echo ----------------------------------------------------

rem Step 1: lichte bootstrap (geen volledige SETUP bij elke start)
echo %CYAAN%[INFO] Bootstrap ^(conda + optioneel RAG-stamp^)...%RESET%
if /I "!CLEAN_ARGS!"=="--setup" goto :run_full_setup
echo !CLEAN_ARGS!| findstr /I "\-\-setup" >nul && goto :run_full_setup
if defined HERMES_RUN_FULL_SETUP_ON_LAUNCH goto :run_full_setup
if defined CLEAN_ARGS (set "HERMES_LAUNCH_ARGS=!CLEAN_ARGS!") else (set "HERMES_LAUNCH_ARGS=")
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%/windows/scripts/launch_bootstrap.ps1" -RepoRoot "%REPO_ROOT%"
if !errorLevel! neq 0 (
    echo %ROOD%[ERROR] Bootstrap mislukt.%RESET%
    pause
    exit /b !errorLevel!
)
goto :after_setup

:run_full_setup
echo %GOUD%[INFO] Volledige setup ^(SETUP_HERMES / --setup^)...%RESET%
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%/scripts/windows/setup_hermes_windows.ps1" !CLEAN_ARGS!
if !errorLevel! neq 0 (
    echo %ROOD%[ERROR] Setup failed. Check hermes_setup.log for details.%RESET%
    echo [%DATE% %TIME%] ERROR: Setup failed with exit code !errorLevel! >> "%LAUNCH_LOG%"
    pause
    exit /b !errorLevel!
)

:after_setup

rem --- SOUL anatomy deploy (14 templates + snippets wanneer repo bron nieuwer dan stamp) ---
if not defined HERMES_SKIP_SOUL_DEPLOY_ON_START (
  set "HERMES_REPO_ROOT=!REPO_ROOT!"
  powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%/windows/scripts/launch_soul_anatomy_deploy.ps1" -RepoRoot "!REPO_ROOT!"
  if !errorLevel! neq 0 (
    echo %GOUD%[WARN] SOUL anatomy deploy mislukt ^(exit !errorLevel!^) — start gaat door.%RESET%
    echo [%DATE% %TIME%] WARN: soul anatomy deploy exit !errorLevel! >> "%LAUNCH_LOG%"
  )
)

rem --- Institutioneel runtime (display alle profielen + SOUL snippets indien nodig; E2E alleen met flag) ---
if not defined HERMES_SKIP_INSTITUTIONAL_RUNTIME (
  set "HERMES_REPO_ROOT=!REPO_ROOT!"
  set "INST_PS_ARGS="
  echo !CLEAN_ARGS!| findstr /I "\-\-institutional-e2e" >nul && set "INST_PS_ARGS=-RunE2E"
  if defined HERMES_INSTITUTIONAL_E2E_ON_START set "INST_PS_ARGS=!INST_PS_ARGS! -RunE2E"
  powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%/windows/scripts/launch_institutional_runtime.ps1" !INST_PS_ARGS!
  if !errorLevel! neq 0 (
    echo %GOUD%[WARN] Institutioneel runtime mislukt ^(exit !errorLevel!^) — start gaat door.%RESET%
    echo [%DATE% %TIME%] WARN: institutional runtime exit !errorLevel! >> "%LAUNCH_LOG%"
  )
)

rem --- Pending trust-nazorg na mislukte UPDATE (licht; geen harde stop) ---
if not defined HERMES_SKIP_PENDING_TRUST_ON_START (
  set "HERMES_REPO_ROOT=!REPO_ROOT!"
  powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%/windows/scripts/launch_pending_trust_runtime.ps1" -RepoRoot "!REPO_ROOT!"
  if !errorLevel! neq 0 (
    echo %GOUD%[WARN] Trust-nazorg mislukt ^(exit !errorLevel!^) — start gaat door.%RESET%
    echo [%DATE% %TIME%] WARN: pending trust runtime exit !errorLevel! >> "%LAUNCH_LOG%"
  )
)

rem --- Web dashboard op 9119 (achtergrond, geen browser-tab) ---
rem --- Optioneel tab openen: set HERMES_DASHBOARD_OPEN_PATH=/sessions of /codebase-viz ---
rem --- Uit: HERMES_SKIP_DASHBOARD_ON_START=1 ---
if not defined HERMES_SKIP_DASHBOARD_ON_START (
  set "HERMES_REPO_ROOT=!REPO_ROOT!"
  set "HERMES_LAUNCH_LOG=!LAUNCH_LOG!"
  powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%/windows/scripts/launch_dashboard_on_start.ps1" -RepoRoot "!REPO_ROOT!" -Quiet
  if !errorLevel! neq 0 (
    echo %GOUD%[WARN] Dashboard start mislukt ^(exit !errorLevel!^) — chat start wel.%RESET%
    echo [%DATE% %TIME%] WARN: dashboard on start exit !errorLevel! >> "%LAUNCH_LOG%"
  )
)

:launch_chat
echo %GROEN%[INFO] Hermes Agent starten...%RESET%
echo [%DATE% %TIME%] Launching runtime wrapper... >> "%LAUNCH_LOG%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ". '%REPO_ROOT%\windows\HermesShellCommon.ps1'; Reset-HermesConsoleInputModes; Invoke-HermesDisableConsoleQuickEdit; [void](Stop-HermesGhostInputBlockers -RepoRoot '%REPO_ROOT%'); try { Clear-Host } catch { }" 2>nul
cls >nul 2>&1

rem --- PREMIUM: Auto-Backup before Update ---
echo "!CLEAN_ARGS!" | findstr /I "update" >nul
if !errorlevel! equ 0 (
    echo %GOUD%[PREMIUM] Update gedetecteerd. Automatische backup wordt gestart voor veiligheid...%RESET%
    powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%/windows/stop_other_hermes_processes.ps1"
    set "HERMES_BACKUP_NONINTERACTIVE=1"
    powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%/windows/backup_hermes.ps1" -SkipPause
    if !errorLevel! neq 0 (
        echo %GOUD%[WARN] Auto-backup overgeslagen of mislukt ^(exit !errorLevel!^) — update gaat door.%RESET%
        echo [%DATE% %TIME%] WARN: auto-backup exit !errorLevel! >> "%LAUNCH_LOG%"
    )
)

rem --- Check if .env exists ---
if not exist "%USERPROFILE%\.hermes\.env" (
    echo %ROOD%[WAARSCHUWING] Geen .env gevonden! Gebruik 'hermes setup' in de agent.%RESET%
)

rem Chat in dezelfde cmd (Win32-safe): prepare schrijft state, hermes_chat.cmd roept python aan.
if defined CLEAN_ARGS (set "HERMES_LAUNCH_ARGS=!CLEAN_ARGS!") else (set "HERMES_LAUNCH_ARGS=")
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\windows\run_hermes_prepare.ps1"
if !errorLevel! neq 0 (
    echo %ROOD%[ERROR] Hermes voorbereiding mislukt. Zie hermes_runtime.log en hermes_last_error.log.%RESET%
    echo [%DATE% %TIME%] ERROR: prepare failed with exit code !errorLevel! >> "%LAUNCH_LOG%"
    pause
    exit /b !errorLevel!
)
call "%REPO_ROOT%\windows\hermes_chat.cmd"
if !errorLevel! neq 0 (
    echo %ROOD%[ERROR] Hermes Agent stopped with an error. Check hermes_runtime.log en hermes_last_error.log.%RESET%
    echo [%DATE% %TIME%] ERROR: chat failed with exit code !errorLevel! >> "%LAUNCH_LOG%"
    pause
    exit /b !errorLevel!
)

rem Exit-summary komt uit Python; alleen muismodi herstellen (geen echo boven summary).
echo [%DATE% %TIME%] Session completed successfully. >> "%LAUNCH_LOG%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ". '%REPO_ROOT%\windows\HermesShellCommon.ps1'; Reset-HermesConsoleInputModes; Invoke-HermesDisableConsoleQuickEdit" 2>nul
if defined HERMES_DEBUG_LAUNCH pause
exit /b 0
