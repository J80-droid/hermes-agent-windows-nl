@echo off
rem Rooktest legal: search_knowledge + optioneel hermes chat (vereist API-login).
rem Args (setlocal-safe): %1=HERMES_REPO, %2=PY — van institutional_p0_p1 / launcher.
rem Fallback: env HERMES_REPO, daarna hermes_agent_repo.txt, dan hardcoded dev-pad.
setlocal EnableExtensions
if not "%~1"=="" set "HERMES_REPO=%~1"
if not "%~2"=="" set "PY=%~2"
if not defined HERMES_REPO (
  if exist "%USERPROFILE%\data\hermes_agent_repo.txt" (
    for /f "usebackq delims=" %%I in ("%USERPROFILE%\data\hermes_agent_repo.txt") do set "HERMES_REPO=%%~I"
  ) else (
    set "HERMES_REPO=D:\A.I\APPS\Hermes_agent_WS\hermes-agent"
  )
)
if not exist "%HERMES_REPO%\pyproject.toml" (
  echo [ERROR] HERMES_REPO ongeldig: %HERMES_REPO%
  endlocal & set "ROOKTEST_CHAT=failed" & exit /b 1
)
if not defined PY set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not exist "%PY%" set "PY=python"
if not exist "%HERMES_REPO%\scripts\rag_pipeline\_rooktest_search.py" (
  echo [ERROR] Rooktest-script ontbreekt: %HERMES_REPO%\scripts\rag_pipeline\_rooktest_search.py
  endlocal & set "ROOKTEST_CHAT=failed" & exit /b 1
)

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
