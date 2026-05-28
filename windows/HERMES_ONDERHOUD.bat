@echo off
setlocal EnableExtensions
rem Eén onderhoudsrun na codewijzigingen (snelkoppelingen + dashboard + Codebase Viz).
rem Opties doorgeven:  HERMES_ONDERHOUD.bat -ShortcutsOnly  |  -DashboardOnly  |  -VerifyChain  |  -OpenCodebaseViz  |  -StartHermes
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes onderhoud
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Invoke-HermesPostChangeMaintenance.ps1" -RepoRoot "%CD%" %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo [ERROR] Onderhoud mislukt - exit %ERR%.
  if not "%HERMES_NONINTERACTIVE%"=="1" pause
  exit /b %ERR%
)
if not "%HERMES_NONINTERACTIVE%"=="1" pause
exit /b 0
