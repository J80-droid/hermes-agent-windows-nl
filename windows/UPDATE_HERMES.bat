@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul

rem ANSI: groen - visueel anders dan start_hermes (goud) en MANAGE_BACKUPS (cyan)
set "ESC= "
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
echo %ESC%[92m====================================================
echo  Hermes Agent: UPDATE - conda hermes-env
echo ====================================================%ESC%[0m

rem Standaard: Miniconda/Anaconda. Pas aan indien nodig (of zet CONDA_EXE handmatig).
set "CONDA_EXE=%USERPROFILE%\miniconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" goto run_update
set "CONDA_EXE=%ProgramData%\anaconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" goto run_update
set "CONDA_EXE=%USERPROFILE%\anaconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" goto run_update
set "CONDA_EXE=%ProgramData%\miniconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" goto run_update
echo [ERROR] conda.exe niet gevonden. Zet CONDA_EXE in UPDATE_HERMES.bat naar jouw pad.
pause
exit /b 1

:run_update
rem --no-capture-output: anders blijft het scherm lang leeg (conda buffert tot het child-proces klaar is).
echo.
echo [INFO] hermes update starten — uitvoer verschijnt nu regel-voor-regel (even geduld tijdens conda/python-start).
echo.
set "PYTHONUNBUFFERED=1"
"%CONDA_EXE%" run -n hermes-env --no-capture-output hermes update
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (
  echo [ERROR] hermes update eindigde met code %ERR%
  pause
  exit /b %ERR%
)
echo [OK] Update klaar.

rem Standaard: team display.* uit team_display.defaults (idempotent). Opt-out: leeg bestand windows\SKIP_TEAM_DISPLAY_AFTER_UPDATE
echo.
if exist "%~dp0SKIP_TEAM_DISPLAY_AFTER_UPDATE" (
  echo [INFO] SKIP_TEAM_DISPLAY_AFTER_UPDATE aangetroffen — team display-defaults overgeslagen.
) else (
  echo [INFO] Team display-defaults toepassen ^(bron: team_display.defaults^)...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_team_display.ps1"
  if errorlevel 1 echo [WARN] apply_team_display.ps1 eindigde met fout — controleer handmatig.
)

pause
exit /b 0
