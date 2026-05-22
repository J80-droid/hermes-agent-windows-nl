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
"%CONDA%" run -n hermes-env --no-capture-output python -m hermes_cli.main profile use %~1 --fix-hermes-home
exit /b %ERRORLEVEL%
