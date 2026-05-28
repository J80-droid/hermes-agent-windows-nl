@echo off
rem Dunne launcher op repo-root. Profielen: windows\launch_profiles.ps1 — zie windows\START.md
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem --- CLI: --full | --minimal | --profile:full | --profile:minimal ---
:parse_launch_args
if "%~1"=="" goto launch_args_done
if /I "%~1"=="--full" set "HERMES_LAUNCH_PROFILE=full" & shift & goto parse_launch_args
if /I "%~1"=="--minimal" set "HERMES_LAUNCH_PROFILE=minimal" & shift & goto parse_launch_args
set "ARG=%~1"
if /I "!ARG:~0,10!"=="--profile:" (
  set "HERMES_LAUNCH_PROFILE=!ARG:~10!"
  shift
  goto parse_launch_args
)

:launch_args_done
set "HERMES_PROFILE_CMD=%TEMP%\hermes_launch_profile.cmd"
if defined HERMES_LAUNCH_PROFILE (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\scripts\Invoke-HermesLaunchProfileEnv.ps1" -RepoRoot "%CD%" -Profile "!HERMES_LAUNCH_PROFILE!" -OutCmdPath "!HERMES_PROFILE_CMD!" -Quiet >nul
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\scripts\Invoke-HermesLaunchProfileEnv.ps1" -RepoRoot "%CD%" -OutCmdPath "!HERMES_PROFILE_CMD!" -Quiet >nul
)
if errorlevel 1 (
  echo [ERROR] Launch-profiel kon niet worden toegepast.
  pause
  exit /b 1
)
if not exist "!HERMES_PROFILE_CMD!" (
  echo [ERROR] Ontbreekt: !HERMES_PROFILE_CMD!
  pause
  exit /b 1
)
call "!HERMES_PROFILE_CMD!"

if not exist "%~dp0windows\launch_hermes.bat" (
  echo [ERROR] windows\launch_hermes.bat ontbreekt. Herstel de map windows\ uit git of backup.
  pause
  exit /b 1
)
call "%~dp0windows\launch_hermes.bat" %*
exit /b %ERRORLEVEL%
