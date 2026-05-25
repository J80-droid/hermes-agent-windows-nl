@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
chcp 65001 >nul
if not defined HERMES_LANCEDB_PATH set "HERMES_LANCEDB_PATH=%USERPROFILE%\data\lancedb\legal"
set "HERMES_LANCEDB=%HERMES_LANCEDB_PATH%"
set "HERMES_LANCEDB_PATH=%HERMES_LANCEDB%"
set "HERMES_RAG_INGEST_LOG=%~dp0rag_ingest_run.log"
echo [INFO] Rapport overgeslagen PDF/PNG (log + bestaand JSON)...
for /f "delims=" %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0resolve_hermes_python.ps1" -RepoRoot "%CD%" -RequirePip 2^>nul') do set "HERMES_PYTHON=%%P"
if not defined HERMES_PYTHON (
  echo [ERROR] Geen conda hermes-env. Draai windows\REPAIR_PYTHON.bat
  pause
  exit /b 1
)
"%HERMES_PYTHON%" scripts\rag_pipeline\report_rag_skipped.py
if errorlevel 1 pause
else pause
exit /b %ERRORLEVEL%
