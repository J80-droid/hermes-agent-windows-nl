@echo off
REM Aanbevolen entry na upstream: git pull + POST_GIT_PULL (sync, trust, SOUL, relaunch in WT).
REM Doorgeeft alle vlaggen aan windows\POST_GIT_PULL.bat (-Full, -SkipRelaunch, enz.).
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul

echo ====================================================
echo  Hermes: git pull + POST_GIT_PULL (sync + relaunch)
echo ====================================================
echo [INFO] Repo: %CD%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%CD%\windows\scripts\which_hermes_repo.ps1" -RepoRoot "%CD%"
if errorlevel 1 (
  echo [WARN] which_hermes_repo: controleer of dit de juiste fork-checkout is.
)

git status --porcelain 2>nul | findstr /R "." >nul
if not errorlevel 1 (
  echo [WARN] Working tree niet schoon — commit/stash vóór pull of gebruik -QuickFix op POST_GIT_PULL.
)

echo [INFO] git pull...
git pull
if errorlevel 1 (
  echo [ERROR] git pull mislukt.
  pause
  exit /b 1
)

call "%CD%\windows\POST_GIT_PULL.bat" %*
exit /b %ERRORLEVEL%
