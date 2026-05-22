@echo off
rem Zelfde LanceDB- en bronmap als ingest / kb_schema / mcp_server (override: zet variabelen vóór dit script).
rem LanceDB per domein via profile MCP (domains.yaml); geen globale default.
if not defined HERMES_RAG_RAW_SOURCE set "HERMES_RAG_RAW_SOURCE=%USERPROFILE%\data\raw_source_files"
rem Subprocessen / gateway: zelfde interpreter als hermes-env (geen kale `python` op PATH met kapotte stdlib).
if not defined HERMES_CONDA_ENV set "HERMES_CONDA_ENV=hermes-env"
if not defined HERMES_PYTHON if exist "%USERPROFILE%\miniconda3\envs\%HERMES_CONDA_ENV%\python.exe" set "HERMES_PYTHON=%USERPROFILE%\miniconda3\envs\%HERMES_CONDA_ENV%\python.exe"
if not defined HERMES_PYTHON if exist "%USERPROFILE%\anaconda3\envs\%HERMES_CONDA_ENV%\python.exe" set "HERMES_PYTHON=%USERPROFILE%\anaconda3\envs\%HERMES_CONDA_ENV%\python.exe"
if not defined HERMES_PYTHON if exist "%LOCALAPPDATA%\miniconda3\envs\%HERMES_CONDA_ENV%\python.exe" set "HERMES_PYTHON=%LOCALAPPDATA%\miniconda3\envs\%HERMES_CONDA_ENV%\python.exe"
if not defined HERMES_PYTHON if exist "%LOCALAPPDATA%\anaconda3\envs\%HERMES_CONDA_ENV%\python.exe" set "HERMES_PYTHON=%LOCALAPPDATA%\anaconda3\envs\%HERMES_CONDA_ENV%\python.exe"
if defined HERMES_PYTHON set "HERMES_PYTHON_ENV=%HERMES_PYTHON%"
rem Institutioneel: split-pane via Windows Terminal (wt). Ontbreekt wt -> zelfde pad als start_hermes.bat.
setlocal EnableExtensions
pushd "%~dp0"
if not exist "start_hermes.bat" (
  echo [ERROR] start_hermes.bat niet gevonden in %CD%
  popd
  exit /b 1
)
if defined HERMES_PYTHON echo [INFO] HERMES_PYTHON=%HERMES_PYTHON%
where wt >nul 2>&1
if errorlevel 1 (
  echo [Hermes] Windows Terminal ^(wt^) niet op PATH — start zonder split-pane.
  call "%~dp0start_hermes.bat" %*
  popd
  exit /b %ERRORLEVEL%
)
if not exist "%USERPROFILE%\.hermes\logs\" mkdir "%USERPROFILE%\.hermes\logs" 2>nul
set "HERMES_LOG=%USERPROFILE%\.hermes\logs\agent.log"
echo [INFO] Split-pane: links=Hermes chat, rechts=agent.log ^(debug^). Voor alleen chat: start_hermes.bat
wt -M -d "%CD%" cmd /k "set COLORTERM=truecolor&& set TERM=xterm-256color&& call start_hermes.bat" ^; split-pane -V -d "%CD%" powershell.exe -NoProfile -Command "Get-Content -LiteralPath '%HERMES_LOG%' -Wait -Tail 30"
popd
endlocal
