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
"%PY%" "%HERMES_REPO%\scripts\rag_pipeline\_rooktest_chat.py"
set "CHAT_EXIT=%ERRORLEVEL%"
if "%CHAT_EXIT%"=="0" (
  endlocal & set "ROOKTEST_CHAT=ok" & exit /b 0
)
if "%CHAT_EXIT%"=="2" (
  endlocal & set "ROOKTEST_CHAT=skipped" & exit /b 0
)
endlocal & set "ROOKTEST_CHAT=failed" & exit /b 0
