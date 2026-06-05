@echo off
rem Sticky profiel wisselen + API-sync + HERMES_HOME-hygiene + gateway (indien actief)
setlocal EnableExtensions
if "%~1"=="" (
  echo Gebruik: SWITCH_PROFILE.bat ^<naam^>
  echo Voorbeeld: SWITCH_PROFILE.bat legal
  echo Direct chat: SWITCH_PROFILE_AND_CHAT.bat ^<naam^>
  exit /b 1
)
set "CONDA=%USERPROFILE%\miniconda3\Scripts\conda.exe"
if not exist "%CONDA%" set "CONDA=%ProgramData%\miniconda3\Scripts\conda.exe"
if not exist "%CONDA%" (
  echo Conda niet gevonden.
  exit /b 1
)
pushd "%~dp0\.."
"%CONDA%" run -n hermes-env --no-capture-output python scripts/run_hermes_cli_with_overlay.py profile use %~1 --fix-hermes-home
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
