@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"

if "%~1"=="" (
  echo Gebruik: RESUME_HERMES.bat ^<session_id^>
  echo Voorbeeld: RESUME_HERMES.bat 20260522_032216_86b6ae
  pause
  exit /b 1
)

if not defined HERMES_CONDA_ENV set "HERMES_CONDA_ENV=hermes-env"
if not defined HERMES_PYTHON if exist "%USERPROFILE%\miniconda3\envs\%HERMES_CONDA_ENV%\python.exe" set "HERMES_PYTHON=%USERPROFILE%\miniconda3\envs\%HERMES_CONDA_ENV%\python.exe"
if not defined HERMES_PYTHON (
  echo [ERROR] Geen conda hermes-env. Zie windows\REPAIR_PYTHON.bat
  pause
  exit /b 1
)

echo [INFO] Resume sessie %~1 via %HERMES_PYTHON%
echo [INFO] Tip: -c met ^< of ^> niet via .bat — typ die prompt in de TUI na resume.
"%HERMES_PYTHON%" -m hermes_cli_entry --resume %1
exit /b %ERRORLEVEL%
