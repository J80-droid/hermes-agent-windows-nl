@echo off
rem Kleuren, [LIVE], UTF-8 log, perf-safe — zelfde stack als institutionele RAG.
setlocal EnableExtensions
call "%~dp0_resolve_hermes_repo.bat"
if errorlevel 1 exit /b 1

if not defined RAG_DOMAIN set "RAG_DOMAIN=rag"
set "WIN_SCR=%HERMES_REPO%\windows\scripts"

if not defined HERMES_LANCEDB_PATH (
  echo [ERROR] HERMES_LANCEDB_PATH niet gezet.
  exit /b 1
)
if not defined HERMES_RAG_RAW_SOURCE (
  echo [ERROR] HERMES_RAG_RAW_SOURCE niet gezet.
  exit /b 1
)

set "LOG_DIR=%USERPROFILE%\data\scripts\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" 2>nul
set "RAG_LOG=%LOG_DIR%\rag_%RAG_DOMAIN%_ingest.log"
set "HERMES_RAG_INGEST_LOG=%RAG_LOG%"

set "PYTHONUNBUFFERED=1"
set "PYTHONUTF8=1"
set "HERMES_FORCE_COLOR=1"
set "FORCE_COLOR=1"
if not defined HERMES_RAG_PERF_PROFILE set "HERMES_RAG_PERF_PROFILE=safe"

for /f "delims=" %%L in ('powershell -NoProfile -ExecutionPolicy Bypass -File "%WIN_SCR%\rag_ingest_perf_defaults.ps1" -EmitCmd 2^>nul') do %%L

powershell -NoProfile -ExecutionPolicy Bypass -File "%WIN_SCR%\check_rag_ingest_running.ps1" 2>nul
if errorlevel 1 (
  echo [ERROR] Er draait al een RAG-ingest. Stop die eerst.
  exit /b 1
)

echo [INFO] Log ^(UTF-8^): %RAG_LOG%
echo [INFO] Live status: %HERMES_LANCEDB_PATH%\rag_ingest_live_status.json

powershell -NoProfile -ExecutionPolicy Bypass -File "%WIN_SCR%\enable_console_ansi.ps1" 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%WIN_SCR%\run_rag_ingest.ps1" -LogPath "%RAG_LOG%" -CondaEnv "hermes-env" -RepoRoot "%HERMES_REPO%"
exit /b %ERRORLEVEL%
