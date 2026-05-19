@echo off

setlocal EnableExtensions

cd /d "%~dp0\.."

chcp 65001 >nul



rem ANSI: magenta [95m] - onderscheid t.o.v. UPDATE (groen) en backups (cyan)

set "ESC= "

for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"

echo %ESC%[95m====================================================

echo  Hermes Agent: DOCTOR --fix (conda hermes-env)

echo ====================================================%ESC%[0m



set "CONDA_EXE=%USERPROFILE%\miniconda3\Scripts\conda.exe"

if exist "%CONDA_EXE%" goto run_doctor

set "CONDA_EXE=%ProgramData%\anaconda3\Scripts\conda.exe"

if exist "%CONDA_EXE%" goto run_doctor

set "CONDA_EXE=%USERPROFILE%\anaconda3\Scripts\conda.exe"

if exist "%CONDA_EXE%" goto run_doctor

set "CONDA_EXE=%ProgramData%\miniconda3\Scripts\conda.exe"

if exist "%CONDA_EXE%" goto run_doctor

echo [ERROR] conda.exe niet gevonden. Pas CONDA_EXE aan (zie UPDATE_HERMES.bat).

pause

exit /b 1



:run_doctor

echo.

set "PYTHONUNBUFFERED=1"

"%CONDA_EXE%" run -n hermes-env --no-capture-output hermes doctor --fix

set ERR=%ERRORLEVEL%

echo.

if %ERR% neq 0 (

  echo [ERROR] hermes doctor --fix eindigde met code %ERR%

  pause

  exit /b %ERR%

)

echo [OK] Doctor --fix klaar.

pause

exit /b 0

