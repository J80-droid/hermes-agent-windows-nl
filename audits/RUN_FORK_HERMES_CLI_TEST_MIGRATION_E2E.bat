@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ForkHermesCliTestMigrationE2E.core.ps1"
if errorlevel 1 exit /b 1
echo RUN_FORK_HERMES_CLI_TEST_MIGRATION_E2E: ALL PASS
exit /b 0
