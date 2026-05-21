@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
chcp 65001 >nul
if not defined HERMES_LANCEDB_PATH set "HERMES_LANCEDB_PATH=%USERPROFILE%\data\lancedb\legal"
set "HERMES_LANCEDB=%HERMES_LANCEDB_PATH%"
set "HERMES_LANCEDB_PATH=%HERMES_LANCEDB%"
set "HERMES_RAG_INGEST_LOG=%~dp0rag_ingest_run.log"
echo [INFO] Rapport overgeslagen PDF/PNG (log + bestaand JSON)...
python scripts\rag_pipeline\report_rag_skipped.py
if errorlevel 1 pause
else pause
exit /b %ERRORLEVEL%
