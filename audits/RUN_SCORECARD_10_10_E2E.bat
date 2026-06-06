@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Scorecard1010E2E.core.ps1"
if errorlevel 1 exit /b 1
echo RUN_SCORECARD_10_10_E2E: ALL PASS
exit /b 0
