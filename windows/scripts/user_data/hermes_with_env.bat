@echo off
rem Hermes CLI via hermes-env (zonder conda activate). Alle args door naar hermes_cli.main.
setlocal EnableExtensions

if not defined HERMES_REPO (
  if exist "%USERPROFILE%\data\hermes_agent_repo.txt" (
    set /p HERMES_REPO=<"%USERPROFILE%\data\hermes_agent_repo.txt"
  ) else (
    set "HERMES_REPO=D:\A.I\APPS\Hermes_agent_WS\hermes-agent"
  )
)

set "PY="
for %%P in (
  "%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
  "%LOCALAPPDATA%\miniconda3\envs\hermes-env\python.exe"
  "%USERPROFILE%\anaconda3\envs\hermes-env\python.exe"
  "C:\ProgramData\miniconda3\envs\hermes-env\python.exe"
) do if not defined PY if exist %%~P set "PY=%%~P"

if not defined PY if defined HERMES_PYTHON if exist "%HERMES_PYTHON%" set "PY=%HERMES_PYTHON%"

if not defined PY (
  echo [ERROR] hermes-env python niet gevonden.
  echo        Verwacht o.a.: %%USERPROFILE%%\miniconda3\envs\hermes-env\python.exe
  echo        Of zet HERMES_PYTHON naar je python.exe
  exit /b 1
)

set "HERMES_PYTHON=%PY%"
set "PATH=%USERPROFILE%\miniconda3\envs\hermes-env;%USERPROFILE%\miniconda3\envs\hermes-env\Scripts;%USERPROFILE%\miniconda3\condabin;%PATH%"

cd /d "%HERMES_REPO%"
"%PY%" -m hermes_cli_entry %*
set "EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %EXIT_CODE%
