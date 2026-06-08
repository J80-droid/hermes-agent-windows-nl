@echo off
rem Eén taak: interactieve Hermes setup-wizard in DIT cmd-venster (echte TTY).
rem Zelfde Python-zoekvolgorde als windows\launch_hermes.bat (Conda hermes-env eerst).
setlocal EnableExtensions EnableDelayedExpansion
title Hermes — volledige setup-wizard
rem Kan staan in repo\windows\ of repo\scripts\windows\ — repo-root = waar cli.py ligt
if exist "%~dp0..\cli.py" (
  cd /d "%~dp0.."
) else if exist "%~dp0..\..\cli.py" (
  cd /d "%~dp0..\.."
) else (
  echo [ERROR] cli.py niet gevonden. OPEN_SETUP.bat hoort in windows\ of scripts\windows\.
  if not defined HERMES_OPEN_SETUP_NOPAUSE pause
  exit /b 1
)

chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"

rem ANSI-logo (anders kleurenschema dan Hermes_met_logo.bat: wit ^> cyaan/magenta/groen)
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
set "C=%ESC%[36m"
set "M=%ESC%[95m"
set "G=%ESC%[92m"
set "A=%ESC%[96m"
set "R=%ESC%[0m"
echo.
echo %C%+------------------------------------------------------------------+%R%
echo %C%^|%R%  %M%  __  __   ____  __  __  ____   ____  %R%   %G%* OPEN SETUP *%R%          %C%^|%R%
echo %C%^|%R%  %M% ^|  ^|/  ^| / ___^|^|  ^|/  ^|^/ ___^| / ___^|%R%  %A% interactieve wizard %R%  %C%^|%R%
echo %C%+------------------------------------------------------------------+%R%
echo.

if not defined HERMES_CONDA_ENV set "HERMES_CONDA_ENV=hermes-env"
if not defined HERMES_PYTHON if exist "%USERPROFILE%\miniconda3\envs\!HERMES_CONDA_ENV!\python.exe" set "HERMES_PYTHON=%USERPROFILE%\miniconda3\envs\!HERMES_CONDA_ENV!\python.exe"
if not defined HERMES_PYTHON if exist "%USERPROFILE%\anaconda3\envs\!HERMES_CONDA_ENV!\python.exe" set "HERMES_PYTHON=%USERPROFILE%\anaconda3\envs\!HERMES_CONDA_ENV!\python.exe"
if not defined HERMES_PYTHON if exist "%LOCALAPPDATA%\miniconda3\envs\!HERMES_CONDA_ENV!\python.exe" set "HERMES_PYTHON=%LOCALAPPDATA%\miniconda3\envs\!HERMES_CONDA_ENV!\python.exe"
if not defined HERMES_PYTHON if exist "%LOCALAPPDATA%\anaconda3\envs\!HERMES_CONDA_ENV!\python.exe" set "HERMES_PYTHON=%LOCALAPPDATA%\anaconda3\envs\!HERMES_CONDA_ENV!\python.exe"
if not defined HERMES_PYTHON if exist "C:\ProgramData\miniconda3\envs\!HERMES_CONDA_ENV!\python.exe" set "HERMES_PYTHON=C:\ProgramData\miniconda3\envs\!HERMES_CONDA_ENV!\python.exe"
if not defined HERMES_PYTHON if exist "C:\ProgramData\anaconda3\envs\!HERMES_CONDA_ENV!\python.exe" set "HERMES_PYTHON=C:\ProgramData\anaconda3\envs\!HERMES_CONDA_ENV!\python.exe"

echo %A%  python -m hermes_cli_entry setup%R%  ^|  repo: %CD%
echo.

rem Zelfde HERMES_HOME als launch_hermes (split-home: %%LOCALAPPDATA%%\hermes).
if exist "windows\scripts\ensure_hermes_launch_env.ps1" (
  echo [INFO] HERMES_HOME alignen met launcher...
  powershell -NoProfile -ExecutionPolicy Bypass -File "windows\scripts\ensure_hermes_launch_env.ps1" -FixUserEnv
  if defined HERMES_HOME echo [INFO] HERMES_HOME=!HERMES_HOME!
)

set "RC=1"
if defined HERMES_PYTHON (
  echo [INFO] Gebruik Conda-python: !HERMES_PYTHON!
  echo [INFO] Console-script hermes aligneren ^(pip install -e^)...
  call "!HERMES_PYTHON!" -m pip install -e "%CD%" -q
  call "!HERMES_PYTHON!" -m hermes_cli_entry setup
  set "RC=!ERRORLEVEL!"
  goto :wiz_done
)
if exist ".venv\Scripts\python.exe" (
  echo [INFO] Gebruik: .venv\Scripts\python.exe
  call ".venv\Scripts\python.exe" -m hermes_cli_entry setup
  set "RC=!ERRORLEVEL!"
  goto :wiz_done
)
if exist ".venv\Scripts\hermes.exe" (
  echo [INFO] Gebruik: .venv\Scripts\python.exe ^(overlay, naast hermes.exe^)
  call ".venv\Scripts\python.exe" -m hermes_cli_entry setup
  set "RC=!ERRORLEVEL!"
  goto :wiz_done
)
where uv >nul 2>&1
if !errorlevel! equ 0 (
  if exist "pyproject.toml" (
    echo [INFO] Gebruik: uv run python ^(repo^)
    call uv run python -m hermes_cli_entry setup
    set "RC=!ERRORLEVEL!"
    goto :wiz_done
  )
)
where hermes >nul 2>&1
if !errorlevel! equ 0 (
  for /f "delims=" %%H in ('where hermes 2^>nul') do (
    if exist "%%~dpHpython.exe" (
      echo [INFO] Gebruik: %%~dpHpython.exe ^(hermes-shim sibling, overlay^)
      call "%%~dpHpython.exe" -m hermes_cli_entry setup
      set "RC=!ERRORLEVEL!"
      goto :wiz_done
    )
  )
)
where python >nul 2>&1
if !errorlevel! equ 0 (
  rem Broken shims / wrong PYTHONHOME often die with "No module named encodings"
  python -c "import encodings" >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] De eerste 'python' op PATH start niet ^(stdlib/import encodings faalde^).
    echo   Vaak oorzaak: PYTHONHOME of PYTHONPATH in Windows-gebruikersomgeving.
    echo   Fix: Verwijder PYTHONHOME ^& heropen cmd, of gebruik conda:
    echo     conda activate %HERMES_CONDA_ENV%
    echo     python -m hermes_cli_entry setup
    echo   Of installeer de env: windows\setup_hermes_windows.bat
    set "RC=1"
    goto :wiz_done
  )
  echo [INFO] Gebruik: python op PATH
  call python -m hermes_cli_entry setup
  set "RC=!ERRORLEVEL!"
  goto :wiz_done
)

echo [ERROR] Geen geschikte Python/hermes gevonden.
echo   Maak conda-env "%HERMES_CONDA_ENV%" aan, of installeer .venv in deze repo.
echo   Zie windows\launch_hermes.bat voor dezelfde paden.
if not defined HERMES_OPEN_SETUP_NOPAUSE pause
exit /b 1

:wiz_done
if !RC! neq 0 (
  echo.
  echo [ERROR] Wizard stopte met code !RC!
) else (
  echo.
  echo [OK] Setup-wizard afgerond.
  echo [INFO] Opgeslagen in %%LOCALAPPDATA%%\hermes\config.yaml - launch leest dit automatisch.
  if exist "windows\scripts\repair_model_provider_coherence.ps1" (
    echo [INFO] Model/provider coherentie controleren...
    powershell -NoProfile -ExecutionPolicy Bypass -File "windows\scripts\repair_model_provider_coherence.ps1" -Quiet
  )
  if defined HERMES_PYTHON (
    echo [INFO] Config-cache legen zodat chat direct OPEN_SETUP-model ziet...
    "!HERMES_PYTHON!" -c "import sys; sys.path.insert(0, r'%CD%'); from overlay.bootstrap import install; install(); from hermes_cli.profile_model_inheritance import bust_config_caches, root_config_path; bust_config_caches(root_config_path())"
  )
  if exist "windows\scripts\HermesHomeCommon.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ". 'windows\scripts\HermesHomeCommon.ps1'; Write-HermesRuntimeModelBanner"
  )
)
if not defined HERMES_OPEN_SETUP_NOPAUSE pause
exit /b !RC!
