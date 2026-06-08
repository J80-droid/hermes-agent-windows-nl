@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul

rem Dit is NIET de conda/pip-repo-setup (zie SETUP_HERMES.bat).
rem Dit start de officiële interactieve Hermes-wizard: model, provider, API-keys, …

set "ESC= "
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
echo %ESC%[93m====================================================
echo  Hermes: interactieve setup (hermes setup)
echo ====================================================%ESC%[0m
echo [INFO] Repo-root: %CD%
echo [INFO] Alleen model wijzigen: na afloop kun je ook "hermes model" gebruiken.
echo.

set "CONDA_EXE=%USERPROFILE%\miniconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" goto run_wizard
set "CONDA_EXE=%ProgramData%\anaconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" goto run_wizard
set "CONDA_EXE=%USERPROFILE%\anaconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" goto run_wizard
set "CONDA_EXE=%ProgramData%\miniconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" goto run_wizard
echo [ERROR] conda.exe niet gevonden. Pas CONDA_EXE aan (zie UPDATE_HERMES.bat).
pause
exit /b 1

:run_wizard
"%CONDA_EXE%" run -n hermes-env --no-capture-output python -m hermes_cli_entry setup %*
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (
  echo [ERROR] hermes setup eindigde met code %ERR%
  pause
  exit /b %ERR%
)
echo [OK] Klaar. Start Hermes opnieuw als de wizard dat vraagt.
pause
exit /b 0
