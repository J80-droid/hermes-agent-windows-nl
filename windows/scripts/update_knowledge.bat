@echo off
rem LanceDB RAG — per-domein via %%USERPROFILE%%\data\domains.yaml
rem Gebruik: update_knowledge.bat [domein| --list | --mcp-test | --media-only]
setlocal EnableExtensions
chcp 65001 >nul
title Hermes RAG - kennis bijwerken

call "%~dp0rag\_resolve_hermes_repo.bat"
if errorlevel 1 goto :finish_err

if /i "%~1"=="--list" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_knowledge.ps1" -List
  set "RAG_EXIT=%ERRORLEVEL%"
  goto :finish
)
if /i "%~1"=="--mcp-test" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_knowledge.ps1" -McpVerifyOnly -All
  set "RAG_EXIT=%ERRORLEVEL%"
  goto :finish
)

if not exist "%USERPROFILE%\data\domains.yaml" (
  echo [ERROR] domains.yaml ontbreekt: %USERPROFILE%\data\domains.yaml
  echo        Kopieer vanuit documentatie of herstel via setup.
  set "RAG_EXIT=1"
  goto :finish
)

if not defined HERMES_RAG_FRESH (
  echo ====================================================
  echo  Hermes RAG - kennis bijwerken
  echo ====================================================
  echo  Config: %USERPROFILE%\data\domains.yaml
  echo.
  echo  J = Frisse start ^(database wissen, alles opnieuw^)
  echo  N = Alleen gewijzigde/nieuwe bestanden ^(snel^)
  echo.
  choice /c JN /n /m "Kies J of N: "
  if errorlevel 2 (set "HERMES_RAG_FRESH=n") else (set "HERMES_RAG_FRESH=j")
)

if /i "%~1"=="--media-only" (
  if "%~2"=="" (
    echo [ERROR] Geef een domein: update_knowledge.bat legal --media-only
    set "RAG_EXIT=1"
    goto :finish
  )
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_knowledge.ps1" -Domain "%~2" -MediaOnly
  goto :after_run
)
if /i "%~2"=="--media-only" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_knowledge.ps1" -Domain "%~1" -MediaOnly
  goto :after_run
)
if "%~1"=="" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_knowledge.ps1" -All
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_knowledge.ps1" -Domain "%~1"
)
:after_run
set "RAG_EXIT=%ERRORLEVEL%"
goto :finish

:finish_err
set "RAG_EXIT=1"

:finish
if /i not "%HERMES_NONINTERACTIVE%"=="1" (
  echo.
  if not "%RAG_EXIT%"=="0" (
    echo [ERROR] RAG-update eindigde met fout ^(exit %RAG_EXIT%^).
  )
  echo Druk op een toets om te sluiten...
  pause >nul
)
exit /b %RAG_EXIT%
