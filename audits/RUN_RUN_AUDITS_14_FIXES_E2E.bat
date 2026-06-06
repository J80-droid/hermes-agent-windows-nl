@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RunAudits14FixesE2E.core.ps1"
if errorlevel 1 exit /b 1
echo RUN_RUN_AUDITS_14_FIXES_E2E: ALL PASS
exit /b 0
