@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\.."
chcp 65001 >nul

echo [INFO] RAG readiness + pipeline...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Get-RagSourceReadiness.ps1" -RepoRoot "%CD%"
if errorlevel 2 (
  echo [INFO] Geen bronbestanden in raw_source_files — plaats bronnen en draai opnieuw.
  exit /b 2
)
if errorlevel 1 (
  echo [ERROR] RAG readiness-check mislukt.
  exit /b 1
)

echo [INFO] institutional_p0_p1.bat --ingest-remaining ...
call "%~dp0scripts\institutional_p0_p1.bat" --ingest-remaining
if errorlevel 1 exit /b 1

echo [INFO] update_knowledge.bat --mcp-test ...
set "HERMES_NONINTERACTIVE=1"
call "%~dp0scripts\update_knowledge.bat" --mcp-test
exit /b %ERRORLEVEL%
