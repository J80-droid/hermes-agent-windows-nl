@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

echo ============================================================
echo   Codebase Viz incremental SWR E2E
echo ============================================================
echo.

set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" "audits\CodebaseVizIncrementalSWRE2E.harness.py"
set "EC=%ERRORLEVEL%"

if not "%EC%"=="0" (
  echo RUN_CODEBASE_VIZ_INCREMENTAL_SWR_E2E: FAIL ^(exit %EC%^)
  exit /b %EC%
)

echo RUN_CODEBASE_VIZ_INCREMENTAL_SWR_E2E: ALL PASS
exit /b 0

