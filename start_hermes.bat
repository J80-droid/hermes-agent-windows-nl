@echo off
rem Eén launcher: start Hermes; pull+sync+relaunch alleen als origin achterloopt.
rem --pull = forceer pull+sync · --sync = alleen POST · --no-pull = geen auto-pull
rem Zie windows\START.md
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1

set "HERMES_START_MODE="
set "HERMES_POST_PULL_ARGS="
set "HERMES_LAUNCH_REMAINING="
set "HERMES_NO_AUTO_PULL=0"

rem --- Launch-modus (--pull / --sync / --no-pull) of profielvlagen ---
:parse_launch_args
if "%~1"=="" goto launch_args_done
if /I "%~1"=="--pull" (
  set "HERMES_START_MODE=pull"
  shift
  goto parse_launch_args
)
if /I "%~1"=="--sync" (
  set "HERMES_START_MODE=sync"
  shift
  goto parse_launch_args
)
if /I "%~1"=="--no-pull" (
  set "HERMES_NO_AUTO_PULL=1"
  shift
  goto parse_launch_args
)
if defined HERMES_START_MODE (
  set "HERMES_POST_PULL_ARGS=!HERMES_POST_PULL_ARGS! %~1"
  shift
  goto parse_launch_args
)
if /I "%~1"=="--full" (
  set "HERMES_LAUNCH_PROFILE=full"
  shift
  goto parse_launch_args
)
if /I "%~1"=="--minimal" (
  set "HERMES_LAUNCH_PROFILE=minimal"
  shift
  goto parse_launch_args
)
set "ARG=%~1"
if /I "!ARG:~0,10!"=="--profile:" (
  set "HERMES_LAUNCH_PROFILE=!ARG:~10!"
  shift
  goto parse_launch_args
)
set "HERMES_LAUNCH_REMAINING=!HERMES_LAUNCH_REMAINING! %~1"
shift
goto parse_launch_args

:launch_args_done
if /I "!HERMES_START_MODE!"=="pull" goto do_git_pull_and_sync
if /I "!HERMES_START_MODE!"=="sync" goto do_post_git_pull_only
if "!HERMES_NO_AUTO_PULL!"=="1" goto apply_launch_profile
call :maybe_auto_pull_before_start
if errorlevel 2 goto apply_launch_profile
if errorlevel 1 goto do_git_pull_and_sync
goto apply_launch_profile

:maybe_auto_pull_before_start
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\scripts\Test-HermesGitPullNeeded.ps1" -RepoRoot "%CD%"
exit /b %ERRORLEVEL%

:do_git_pull_and_sync
chcp 65001 >nul
echo ====================================================
echo  Hermes: git pull + POST_GIT_PULL (sync + relaunch)
echo ====================================================
echo [INFO] Repo: %CD%
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\scripts\which_hermes_repo.ps1" -RepoRoot "%CD%"
if errorlevel 1 (
  echo [WARN] which_hermes_repo: controleer of dit de juiste fork-checkout is.
)
git status --porcelain 2>nul | findstr /R "." >nul
if not errorlevel 1 (
  echo [WARN] Working tree niet schoon - commit/stash vóór pull of gebruik -QuickFix op POST_GIT_PULL.
)
echo [INFO] git pull...
git pull
if errorlevel 1 (
  echo [ERROR] git pull mislukt.
  pause
  exit /b 1
)

:do_post_git_pull_only
if not exist "%~dp0windows\POST_GIT_PULL.bat" (
  echo [ERROR] windows\POST_GIT_PULL.bat ontbreekt.
  pause
  exit /b 1
)
call "%~dp0windows\POST_GIT_PULL.bat"!HERMES_POST_PULL_ARGS!
set "POST_RC=!ERRORLEVEL!"
if not "!POST_RC!"=="0" exit /b !POST_RC!
call :should_continue_after_post_pull
if errorlevel 1 goto apply_launch_profile
exit /b 0

:should_continue_after_post_pull
rem POST_GIT_PULL relauncht standaard — dan niet opnieuw launch_hermes aanroepen.
if /I "%HERMES_SKIP_RELAUNCH_AFTER_PULL%"=="1" exit /b 1
echo !HERMES_POST_PULL_ARGS! | findstr /I /C:"-SkipRelaunch" >nul
if not errorlevel 1 exit /b 1
exit /b 0

:apply_launch_profile
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
call "%~dp0windows\launch_hermes.bat"!HERMES_LAUNCH_REMAINING!
exit /b %ERRORLEVEL%
