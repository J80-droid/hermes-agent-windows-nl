@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - diagnose renderer

REM Runtime diagnose van de institutionele renderer.
REM Toont actief profiel, palet, renderer-stijl, en visuele preview.
REM Opties:
REM   --show-palettes   Preview alle geregistreerde paletten
REM   --verify          Exit 0 alleen als institutional_rich + demo actief zijn

set "PY=%HERMES_PYTHON%"
if not defined PY if exist "%USERPROFILE%\miniconda3\envs\hermes-env\python.exe" set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\miniconda3\envs\hermes-env\python.exe" set "PY=%LOCALAPPDATA%\miniconda3\envs\hermes-env\python.exe"
if not defined PY (
  echo [ERROR] hermes-env python niet gevonden
  exit /b 1
)

"%PY%" "%~dp0scripts\diagnose_renderer.py" %*
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo [ERROR] Diagnose faalde met exit %ERR%
  if not "%HERMES_SKIP_PAUSE%"=="1" pause
  exit /b %ERR%
)
if not "%HERMES_SKIP_PAUSE%"=="1" pause
exit /b 0
