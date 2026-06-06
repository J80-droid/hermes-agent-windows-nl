@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RagMinimalFixtureE2E.core.ps1"
if errorlevel 1 exit /b 1
echo RUN_RAG_MINIMAL_FIXTURE_E2E: ALL PASS
exit /b 0
