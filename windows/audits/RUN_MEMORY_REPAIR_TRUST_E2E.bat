@echo off
setlocal
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\..\audits\MemoryRepairTrustE2E.core.ps1"
if errorlevel 1 exit /b 1
echo RUN_MEMORY_REPAIR_TRUST_E2E: ALL PASS
exit /b 0
