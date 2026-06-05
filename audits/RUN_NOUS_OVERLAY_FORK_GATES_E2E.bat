@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0NousOverlayForkGatesE2E.core.ps1"
if errorlevel 1 exit /b 1
echo RUN_NOUS_OVERLAY_FORK_GATES_E2E: ALL PASS
exit /b 0
