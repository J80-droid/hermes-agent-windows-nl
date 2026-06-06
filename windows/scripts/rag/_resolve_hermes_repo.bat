@echo off
rem Zet HERMES_REPO naar hermes-agent root (map met pyproject.toml).
if defined HERMES_REPO if exist "%HERMES_REPO%\pyproject.toml" exit /b 0
set "HERMES_REPO=%~dp0..\..\.."
if exist "%HERMES_REPO%\pyproject.toml" exit /b 0
if exist "%USERPROFILE%\data\hermes_agent_repo.txt" (
  rem for /f trimt CRLF/spaties (set /p laat vaak trailing newline achter)
  for /f "usebackq delims=" %%I in ("%USERPROFILE%\data\hermes_agent_repo.txt") do set "HERMES_REPO=%%~I"
  if exist "%HERMES_REPO%\pyproject.toml" exit /b 0
)
echo [ERROR] HERMES_REPO niet gevonden. Zet env HERMES_REPO of %USERPROFILE%\data\hermes_agent_repo.txt
exit /b 1
