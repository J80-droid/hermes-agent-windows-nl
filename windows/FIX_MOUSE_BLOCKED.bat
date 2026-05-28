@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
echo [INFO] Hermes ghost-vensters opruimen (muisklik geblokkeerd)...
set "HERMES_DISMISS_GHOST_CONSOLES=1"
set "HERMES_NO_PAUSE=1"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  ". 'windows\HermesShellCommon.ps1'; $n = Stop-HermesGhostInputBlockers -RepoRoot '%CD%'; $g = Invoke-HermesDismissGhostConsoleWindows; Invoke-HermesFocusConsoleWindow; Write-Host ('[OK] Dashboard/ghost opgeruimd (processen=' + $n + ', consoles=' + $g + ')') -ForegroundColor Green"
echo [INFO] Als muisklik nog vastzit: Alt+Tab naar Hermes-chat en minimaliseer, of log uit/in.
if /I not "%HERMES_NO_PAUSE%"=="1" pause
