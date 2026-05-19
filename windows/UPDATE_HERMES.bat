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
rem NousResearch upstream/main mergen (niet alleen fork origin). Zie windows\UPSTREAM_SYNC.md
set "HERMES_UPDATE_FROM_UPSTREAM=1"
rem Voorkomt "Toegang geweigerd" op hermes.exe tijdens uv pip (andere vensters/gateway).
echo [INFO] Andere Hermes-processen stoppen ^(gateway, open sessies^)...
"%CONDA_EXE%" run -n hermes-env --no-capture-output hermes gateway stop 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_other_hermes_processes.ps1"
if errorlevel 1 echo [WARN] Kon niet alle Hermes-processen stoppen; update gaat door.
rem --no-capture-output: anders blijft het scherm lang leeg (conda buffert tot het child-proces klaar is).
echo.
echo [INFO] hermes update — NousResearch upstream/main + dependencies
echo [INFO] Uitvoer verschijnt regel-voor-regel (even geduld tijdens conda/python-start).
echo.
set "PYTHONUNBUFFERED=1"
"%CONDA_EXE%" run -n hermes-env --no-capture-output hermes update -y
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (
  echo [ERROR] hermes update eindigde met code %ERR%
  echo [INFO] Bij merge-conflicten: zie windows\UPSTREAM_SYNC.md — hermes werkt weer na oplossen.
  pause
  exit /b %ERR%
)
echo [OK] Update klaar.

rem Team display-defaults (geen %% in REM: anders wordt %%dis%% leeg en draait cmd "play.*")
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
