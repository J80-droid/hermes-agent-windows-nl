@echo off
setlocal EnableExtensions
if /i "%~2"=="--quiet" set "HERMES_NONINTERACTIVE=1"
if /i "%~1"=="--quiet" (
  set "HERMES_NONINTERACTIVE=1"
  set "DOMAIN=legal"
) else (
  set "DOMAIN=%~1"
)
if "%DOMAIN%"=="" set "DOMAIN=legal"
if "%DOMAIN%"=="--quiet" set "DOMAIN=legal"
if not defined HERMES_REPO (
  if exist "%USERPROFILE%\data\hermes_agent_repo.txt" (
    set /p HERMES_REPO=<"%USERPROFILE%\data\hermes_agent_repo.txt"
  ) else (
    set "HERMES_REPO=D:\A.I\APPS\Hermes_agent_WS\hermes-agent"
  )
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_REPO%\windows\scripts\user_data\check_ingest_status.ps1" -Domain "%DOMAIN%"
set "CHK_EXIT=%ERRORLEVEL%"
if /i not "%HERMES_NONINTERACTIVE%"=="1" (
  pause
) else (
  exit /b %CHK_EXIT%
)
exit /b %CHK_EXIT%
