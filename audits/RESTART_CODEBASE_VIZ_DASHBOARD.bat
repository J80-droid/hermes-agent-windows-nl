@echo off
setlocal
REM Stop ALLE hermes-dashboard processen en start opnieuw met workspace plugin (240s pygount).
cd /d "%~dp0.."
set "ROOT=%CD%"
set "HERMES_BUNDLED_PLUGINS=%ROOT%\plugins"
set "CODEBASE_VIZ_PYGOUNT_TIMEOUT=240"

set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
set "CONDA=%USERPROFILE%\miniconda3\Scripts\conda.exe"
if not exist "%PY%" (
  echo hermes-env python niet gevonden: %PY%
  exit /b 1
)

echo === Codebase Viz dashboard herstart ===
echo Repo: %ROOT%
echo.

echo [1/4] Stop alle dashboard-processen...
"%PY%" -m hermes_cli.main dashboard --stop 2>nul
if exist "%CONDA%" (
  "%CONDA%" run -n hermes-env --no-capture-output python -m hermes_cli.main dashboard --stop 2>nul
)
ping -n 4 127.0.0.1 >nul

echo [2/4] Installeer workspace + web deps + pygount...
"%PY%" -m pip install -e "%ROOT%[web]" -q
if errorlevel 1 exit /b 1
"%PY%" -m pip install pygount -q
if errorlevel 1 exit /b 1

echo [3/4] Start dashboard (geen browser)...
start "Hermes dashboard" /MIN cmd /c "set HERMES_BUNDLED_PLUGINS=%HERMES_BUNDLED_PLUGINS%&& set CODEBASE_VIZ_PYGOUNT_TIMEOUT=240&& cd /d %ROOT%&& \"%PY%\" -m hermes_cli.main dashboard --no-open --host 127.0.0.1 --port 9119"

echo Wacht op server...
ping -n 22 127.0.0.1 >nul

echo [4/4] Health verify...
"%PY%" "%ROOT%\audits\verify_codebase_viz_health.py"
if errorlevel 1 (
  echo.
  echo MISLUKT - open http://127.0.0.1:9119/api/plugins/codebase-viz/health in browser
  echo Verwacht: pygount_timeout_sec = 240, version = 2.5.0
  exit /b 1
)

echo.
echo OK. Hard-refresh http://127.0.0.1:9119/codebase-viz (Ctrl+Shift+R)
echo Klik Opnieuw proberen of druk r in de UI.
exit /b 0
