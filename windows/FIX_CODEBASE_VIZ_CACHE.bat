@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
echo [INFO] Codebase Viz pygount-cache repareren (verwijdert ongeldige cache, bouwt opnieuw)...
echo [INFO] Repo: %CD%
echo [INFO] Dit kan enkele minuten duren bij eerste opbouw.
set "HERMES_NO_PAUSE=1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Repair-CodebaseVizPygountCache.ps1" -RepoRoot "%CD%"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo [FAIL] Pygount-cache repair mislukt (exit %RC%). Zie output hierboven.
  if /I not "%HERMES_NO_PAUSE%"=="1" pause
  exit /b %RC%
)
echo [OK] Pygount-cache gerepareerd. Start Hermes opnieuw met start_hermes.bat
if /I not "%HERMES_NO_PAUSE%"=="1" pause
exit /b 0
