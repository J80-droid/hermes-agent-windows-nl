@echo off

setlocal EnableExtensions

cd /d "%~dp0.."

echo [INFO] Hermes muisklik-herstel (overlay + VT + dashboard)...

set "HERMES_DISMISS_GHOST_CONSOLES=1"

set "HERMES_DASHBOARD_USE_NOWINDOW=1"

set "HERMES_NO_PAUSE=1"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^

  ". 'windows\HermesShellCommon.ps1'; $n = Invoke-HermesFixMouseBlocked -RepoRoot '%CD%'; Write-Host ('[OK] Console hersteld (ghost vensters geminimaliseerd: ' + $n + ')') -ForegroundColor Green; Write-Host '[INFO] Sluit ALLE cmd/WT-tabbladen. Start daarna start_hermes.bat (Windows Terminal).' -ForegroundColor Cyan; Write-Host '[INFO] Titelbalk: klik op Windows Terminal (niet zwart vlak). Markeermodus uit: Ctrl+Shift+M' -ForegroundColor DarkGray"

if /I not "%HERMES_NO_PAUSE%"=="1" pause

