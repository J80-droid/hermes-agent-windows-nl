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

rem --- Genereer ESC karakter voor kleuren ---
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
set "GOUD=%ESC%[93m"
set "CYAAN=%ESC%[96m"
set "GROEN=%ESC%[92m"
set "ROOD=%ESC%[91m"
set "RESET=%ESC%[0m"

if defined HERMES_PYTHON echo %CYAAN%[INFO] HERMES_PYTHON=!HERMES_PYTHON! ^(gateway / tool-subprocessen^)%RESET%

rem --- Optioneel: Forceer Windows Terminal voor de beste ervaring ---
if not defined WT_SESSION (
    where wt.exe >nul 2>&1
    if %errorlevel% equ 0 (
        echo %CYAAN%[INFO] Relaunching in Windows Terminal...%RESET%
        start wt -M -d "%REPO_ROOT%" cmd /c "\"%SCRIPT_SELF%\" %*"
        exit /b
    )
)

rem ====================================================
rem  Hermes Agent - Institutional Launcher (v1.5)
rem ====================================================
echo %GOUD%
echo  ====================================================
echo   HERMES AGENT - WINDOWS PREMIUM LAUNCHER
echo  ====================================================
echo %RESET%

set "LAUNCH_LOG=%REPO_ROOT%\hermes_launch.log"

rem --- Filter internal --maximized flag from arguments ---
set "CLEAN_ARGS=%*"
if defined CLEAN_ARGS set "CLEAN_ARGS=!CLEAN_ARGS:--maximized=!"

rem Initialize Logging safely with Rotation (Max 1MB)
if exist "%LAUNCH_LOG%" (
    for %%I in ("%LAUNCH_LOG%") do if %%~zI geq 1048576 (
        echo [%DATE% %TIME%] --- LOG ROTATED - MAX SIZE REACHED --- > "%LAUNCH_LOG%"
    )
)
echo [%DATE% %TIME%] --- NEW LAUNCH SESSION --- >> "%LAUNCH_LOG%" 2>nul

rem 1. Recursive Loop Protection & Window Maximization
if "%~1"=="--maximized" set "HERMES_MAX_FLAG=1"
if "!HERMES_MAX_FLAG!"=="1" goto :check_elevation

echo %CYAAN%[INFO] Maximizing window...%RESET%
start "" /max "%ComSpec%" /k pushd "%REPO_ROOT%" ^&^& set HERMES_MAX_FLAG=1 ^&^& call "%SCRIPT_SELF%" --maximized !CLEAN_ARGS!
exit /b

:check_elevation
rem 2. Request Administrator privileges (UAC Popup)
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo %CYAAN%[INFO] Requesting Administrator privileges - UAC...%RESET%
    echo [%DATE% %TIME%] Requesting elevation... >> "%LAUNCH_LOG%"
    powershell -Command "Start-Process -FilePath '%SCRIPT_SELF%' -ArgumentList '--maximized !CLEAN_ARGS!' -Verb RunAs -WindowStyle Maximized -WorkingDirectory '%REPO_ROOT%'"
    if !errorLevel! neq 0 (
        echo [ERROR] Elevation request failed or was cancelled.
        pause
    )
    exit /b
)

:run_agent
shift
cd /d "%REPO_ROOT%"
echo %CYAAN%[INFO] Environment: Administrator%RESET%
echo %CYAAN%[INFO] Window State: Maximized%RESET%
echo %CYAAN%[INFO] Directory: %CD%%RESET%
echo ----------------------------------------------------

rem ==========================================
rem  Docker Auto-Start & Verification
rem ==========================================
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
echo ----------------------------------------------------

echo %CYAAN%[INFO] Step 1: Running environment setup...%RESET%
rem Setup: canoniek scripts/windows/setup_hermes_windows.ps1 (windows/setup_hermes_windows.ps1 = wrapper).
rem Optional Hermes *config* wizard: run windows/setup_hermes_windows.bat --full-setup from cmd (not the same as this step).
rem Optional flags on this ps1 ^(pip/submodules/doctor^): --full-setup, --pip-only, --with-doctor, etc.
rem Optional: --pip-only, --with-doctor, --skip-submodules, --skip-tinker (minimal), --force-tinker (retry na fout)
rem Model/API/config-wizard: windows\HERMES_SETUP_WIZARD.bat (hermes setup) — niet hetzelfde als deze stap.
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%/scripts/windows/setup_hermes_windows.ps1" !CLEAN_ARGS!
if !errorLevel! neq 0 (
    echo %ROOD%[ERROR] Setup failed. Check hermes_setup.log for details.%RESET%
    echo [%DATE% %TIME%] ERROR: Setup failed with exit code !errorLevel! >> "%LAUNCH_LOG%"
    pause
    exit /b !errorLevel!
)

echo %GROEN%[INFO] Step 2: Launching Hermes Agent...%RESET%
echo [%DATE% %TIME%] Launching runtime wrapper... >> "%LAUNCH_LOG%"

rem --- PREMIUM: Auto-Backup before Update ---
echo "!CLEAN_ARGS!" | findstr /I "update" >nul
if %errorlevel% equ 0 (
    echo %GOUD%[PREMIUM] Update gedetecteerd. Automatische backup wordt gestart voor veiligheid...%RESET%
    powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\windows\backup_hermes.ps1"
)

rem --- Check if .env exists ---
if not exist "%USERPROFILE%\.hermes\.env" (
    echo %ROOD%[WAARSCHUWING] Geen .env gevonden! Gebruik 'hermes setup' in de agent.%RESET%
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\windows\run_hermes.ps1" !CLEAN_ARGS!
if !errorLevel! neq 0 (
    echo %ROOD%[ERROR] Hermes Agent stopped with an error. Check hermes_runtime.log.%RESET%
    echo [%DATE% %TIME%] ERROR: Runtime failed with exit code !errorLevel! >> "%LAUNCH_LOG%"
    pause
    exit /b !errorLevel!
)

echo [INFO] Session ended normally.
echo [%DATE% %TIME%] Session completed successfully. >> "%LAUNCH_LOG%"
pause
