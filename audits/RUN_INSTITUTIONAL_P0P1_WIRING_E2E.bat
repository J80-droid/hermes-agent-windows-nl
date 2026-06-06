@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0InstitutionalP0P1WiringE2E.core.ps1"
if errorlevel 1 exit /b 1
echo RUN_INSTITUTIONAL_P0P1_WIRING_E2E: ALL PASS
exit /b 0
