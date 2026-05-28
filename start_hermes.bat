@echo off
rem Dunne launcher op repo-root. Zie windows\START.md en windows\TERMINAL_WINDOWS.md
setlocal EnableExtensions
cd /d "%~dp0"
rem Geen dubbele relaunch-flits bij dubbelklik (zelfde venster blijft open).
if not defined HERMES_MAX_FLAG set "HERMES_MAX_FLAG=1"
rem Snelle interactieve start (geen Docker/WSL, geen zware GPU-probes, Ollama niet wakkeren).
if not defined HERMES_SKIP_DASHBOARD_ON_START set "HERMES_SKIP_DASHBOARD_ON_START=1"
if not defined HERMES_SKIP_DOCKER_ON_START set "HERMES_SKIP_DOCKER_ON_START=1"
if not defined HERMES_SKIP_HARDWARE_PROBE set "HERMES_SKIP_HARDWARE_PROBE=1"
if not defined HERMES_NO_WAKE_LOCAL_LLM set "HERMES_NO_WAKE_LOCAL_LLM=1"
rem Geen zware pre-chat fases (voorkomt tekst die bovenaan overschrijft).
if not defined HERMES_SKIP_SOUL_DEPLOY_ON_START set "HERMES_SKIP_SOUL_DEPLOY_ON_START=1"
if not defined HERMES_SKIP_INSTITUTIONAL_RUNTIME set "HERMES_SKIP_INSTITUTIONAL_RUNTIME=1"
if not defined HERMES_SKIP_PENDING_TRUST_ON_START set "HERMES_SKIP_PENDING_TRUST_ON_START=1"
if not defined HERMES_MINIMAL_LAUNCH set "HERMES_MINIMAL_LAUNCH=1"
rem Gemaximaliseerd werkgebied (taakbalk zichtbaar), geen 88%% venster / geen F11-fullscreen.
if not defined HERMES_CONSOLE_LAYOUT set "HERMES_CONSOLE_LAYOUT=maximized"
rem Start in Windows Terminal wanneer wt.exe beschikbaar is (zie windows\requirements-windows.txt).
if not defined HERMES_AUTO_WINDOWS_TERMINAL set "HERMES_AUTO_WINDOWS_TERMINAL=1"
if not exist "%~dp0windows\launch_hermes.bat" (
  echo [ERROR] windows\launch_hermes.bat ontbreekt. Herstel de map windows\ uit git of backup.
  pause
  exit /b 1
)
call "%~dp0windows\launch_hermes.bat" %*
exit /b %ERRORLEVEL%
