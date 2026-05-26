@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul

set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo   Institutioneel hardening E2E
echo ============================================================
echo.

"%PY%" "%~dp0InstitutionalHardeningE2E.harness.py"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo RUN_INSTITUTIONAL_HARDENING_E2E: FAIL exit %ERR%
  exit /b %ERR%
)

echo.
echo RUN_INSTITUTIONAL_HARDENING_E2E: ALL PASS
exit /b 0
