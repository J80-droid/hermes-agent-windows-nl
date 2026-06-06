@echo off
rem Institutionele P0+P1-pipeline (geen shortcuts).
rem  1) Sync mcp_servers vanuit domains.yaml naar alle profielen
rem  2) doctor --fix (model + legacy MCP)
rem  3) MCP-probe alle domeinen
rem  4) Legal rooktest (LanceDB + chat)
rem  5) Optioneel: bulk ingest overige domeinen (--ingest-remaining)
rem  6) Optioneel: Kanban legal (--kanban, alleen na geslaagde chat)
setlocal EnableExtensions
chcp 65001 >nul
title Hermes institutional P0+P1

rem Vast script-pad vóór doctor (cwd kan wijzigen na hermes doctor --fix).
set "INST_SCRIPT_DIR=%~dp0"

call "%INST_SCRIPT_DIR%rag\_resolve_hermes_repo.bat"
if errorlevel 1 exit /b 1
call "%INST_SCRIPT_DIR%rag\_rag_apply_institutional_env.bat"

set "UPDATE_KNOWLEDGE_BAT=%INST_SCRIPT_DIR%update_knowledge.bat"
if not exist "%UPDATE_KNOWLEDGE_BAT%" (
  set "UPDATE_KNOWLEDGE_BAT=%HERMES_REPO%\windows\scripts\update_knowledge.bat"
)
if not exist "%UPDATE_KNOWLEDGE_BAT%" (
  echo [ERROR] update_knowledge.bat ontbreekt: %UPDATE_KNOWLEDGE_BAT%
  exit /b 1
)

set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not exist "%PY%" set "PY=python"
set "HERMES_NONINTERACTIVE=1"
set "HERMES_REPO=%HERMES_REPO%"

set "DO_INGEST=0"
set "DO_KANBAN=0"
:parse
if "%~1"=="" goto :run
if /i "%~1"=="--ingest-remaining" set "DO_INGEST=1"
if /i "%~1"=="--kanban" set "DO_KANBAN=1"
shift
goto :parse

:run
echo.
echo ====================================================
echo  Hermes institutional P0+P1
echo ====================================================
echo Repo: %HERMES_REPO%
echo.

echo [STEP 1/5] Sync mcp_servers vanuit domains.yaml
"%PY%" "%HERMES_REPO%\scripts\rag_pipeline\sync_profile_mcp_from_domains.py"
if errorlevel 1 exit /b 1

echo.
echo [STEP 2/5] hermes doctor --fix
"%PY%" -m hermes_cli.main doctor --fix
if errorlevel 1 (
  echo [WARN] doctor --fix exit %ERRORLEVEL% — controleer handmatig
)
echo [INFO] Doctor npm-waarschuwingen ^(agent-browser^) zijn niet blokkerend — optioneel: windows\REPAIR_BROWSER_NPM.bat

echo.
echo [STEP 3/5] MCP-probe alle domeinen
set "UPDATE_KNOWLEDGE_BAT=%INST_SCRIPT_DIR%update_knowledge.bat"
if not exist "%UPDATE_KNOWLEDGE_BAT%" set "UPDATE_KNOWLEDGE_BAT=%HERMES_REPO%\windows\scripts\update_knowledge.bat"
if not exist "%UPDATE_KNOWLEDGE_BAT%" (
  echo [ERROR] update_knowledge.bat ontbreekt: %UPDATE_KNOWLEDGE_BAT%
  exit /b 1
)
call "%UPDATE_KNOWLEDGE_BAT%" --mcp-test
if errorlevel 1 exit /b 1

echo.
echo [STEP 4/5] Legal rooktest
call "%~dp0user_data\hermes_legal_rooktest.bat"
set "ROOK_EXIT=%ERRORLEVEL%"

if "%DO_KANBAN%"=="1" (
  if not "%ROOK_EXIT%"=="0" (
    echo [SKIP] Kanban: rooktest niet volledig geslaagd
  ) else (
    echo.
    echo [STEP 5a] Kanban legal
    call "%~dp0user_data\kanban_legal_zorgplicht.bat"
  )
) else (
  echo [INFO] Kanban overgeslagen ^(geen --kanban^)
)

if "%DO_INGEST%"=="1" (
  echo.
  echo [STEP 5b] Preflight bronmappen ^(7 domeinen^)
  "%PY%" "%HERMES_REPO%\scripts\rag_pipeline\ingest_preflight.py" --only academics operations trading gaming philosophy logistics ventures --skip-empty
  if errorlevel 1 (
    echo [WARN] Een of meer bronmappen zijn leeg — alleen domeinen met bronnen worden geingest.
    echo        Vul %%USERPROFILE%%\data\raw_source_files\ en herhaal --ingest-remaining.
    if not "%HERMES_NONINTERACTIVE%"=="1" pause
  )
  echo.
  echo [STEP 5c] Bulk ingest overige domeinen ^(incrementeel, skip leeg^)
  set "HERMES_RAG_FRESH=n"
  "%PY%" "%HERMES_REPO%\scripts\rag_pipeline\run_domains_ingest.py" --ingest-remaining
  if errorlevel 1 exit /b 1
  echo.
  echo [INFO] Herhaal MCP-probe na bulk ingest...
  call "%UPDATE_KNOWLEDGE_BAT%" --mcp-test
) else (
  echo [INFO] Bulk ingest overgeslagen ^(gebruik --ingest-remaining^)
)

echo.
if "%ROOK_EXIT%"=="0" (
  echo [OK] Institutional P0+P1 afgerond
  exit /b 0
)
echo [WARN] Pipeline klaar; legal chat-rooktest had waarschuwingen ^(zie boven^)
exit /b 0
