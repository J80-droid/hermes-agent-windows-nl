@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0TerminalCwdMigrationE2E.core.ps1"
if errorlevel 1 exit /b 1
echo RUN_TERMINAL_CWD_MIGRATION_E2E: ALL PASS
exit /b 0
