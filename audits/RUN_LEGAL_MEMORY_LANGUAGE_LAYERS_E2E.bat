@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul

set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not exist "%PY%" set "PY=python"

echo [INFO] Legal Memory Language Layers E2E (EN trust + NL triggers, geen i18n)...
"%PY%" "%~dp0LegalMemoryLanguageLayersE2E.harness.py"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo RUN_LEGAL_MEMORY_LANGUAGE_LAYERS_E2E: FAIL exit %ERR%
  exit /b %ERR%
)
echo RUN_LEGAL_MEMORY_LANGUAGE_LAYERS_E2E: ALL PASS
exit /b 0
