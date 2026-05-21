@echo off
rem Kanban: legal analyse actieve zorgplicht — NA voltooide legal ingest.
setlocal EnableExtensions

set "HERMES_HOME=%LOCALAPPDATA%\hermes\profiles\legal"
set "TASK_TITLE=Analyseer schending actieve zorgplicht in P-Direkt dossier"
set "TASK_BODY=Doorzoek de knowledge base op actieve zorgplicht, re-integratie en 104 weken. Maak een formeel overzicht (Feitelijke handeling vs Toepasselijke norm) gebaseerd op GCR 2024-00145. Citeer exacte bestandsnamen uit search_knowledge."

echo.
echo [INFO] Kanban legal — actieve zorgplicht
echo =======================================
echo Profiel: %HERMES_HOME%
echo.
echo [WARN] Draai dit NIET terwijl update_knowledge.bat legal nog draait (LanceDB-lock).
echo.

where hermes >nul 2>&1
if errorlevel 1 (
  echo [ERROR] hermes niet in PATH. Activeer conda: conda activate hermes-env
  echo.
  echo Handmatig:
  echo   set HERMES_HOME=%HERMES_HOME%
  echo   hermes kanban create "%TASK_TITLE%" --assignee legal --body "%TASK_BODY%"
  echo   hermes kanban dispatch
  pause
  exit /b 1
)

set "HERMES_HOME=%HERMES_HOME%"
echo [INFO] Taak aanmaken...
hermes kanban create "%TASK_TITLE%" --assignee legal --body "%TASK_BODY%"
if errorlevel 1 (
  echo [ERROR] kanban create mislukt
  pause
  exit /b 1
)

echo.
echo [INFO] Dispatcher starten (Ctrl+C om te stoppen)...
hermes kanban dispatch

endlocal
