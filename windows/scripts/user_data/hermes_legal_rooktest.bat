@echo off
rem Rooktest legal: search_knowledge + optioneel hermes chat (vereist API-login).
setlocal EnableExtensions
if not defined HERMES_REPO (
  if exist "%USERPROFILE%\data\hermes_agent_repo.txt" (
    set /p HERMES_REPO=<"%USERPROFILE%\data\hermes_agent_repo.txt"
  ) else (
    set "HERMES_REPO=D:\A.I\APPS\Hermes_agent_WS\hermes-agent"
  )
)
set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not exist "%PY%" set "PY=python"

echo [INFO] 1/2 LanceDB search_knowledge (geen API nodig)
"%PY%" "%HERMES_REPO%\scripts\rag_pipeline\_rooktest_search.py"
if errorlevel 1 (
  echo [ERROR] search_knowledge rooktest mislukt
  exit /b 1
)
echo [OK] search_knowledge rooktest geslaagd
echo.
echo [INFO] 2/2 Hermes chat (vereist inference-login: hermes login)
set "HERMES_YOLO_MODE=1"
set "HERMES_NONINTERACTIVE=1"
cd /d "%HERMES_REPO%"
"%PY%" -m hermes_cli.main -p legal chat -q "Voer search_knowledge uit op actieve zorgplicht P-Direkt en citeer met [Bron: bestandsnaam]." -Q --yolo --max-turns 8
set "CHAT_EXIT=%ERRORLEVEL%"
if "%CHAT_EXIT%"=="0" (
  echo [OK] Hermes chat rooktest geslaagd
) else (
  echo [WARN] Hermes chat exit %CHAT_EXIT% — vaak 401 zonder API-key. LanceDB-deel is wel OK.
)
exit /b 0
