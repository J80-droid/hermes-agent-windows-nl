@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0NousOverlayInstitutionalE2E.core.ps1"
if errorlevel 1 exit /b 1
echo RUN_NOUS_OVERLAY_INSTITUTIONAL_E2E: ALL PASS
exit /b 0
