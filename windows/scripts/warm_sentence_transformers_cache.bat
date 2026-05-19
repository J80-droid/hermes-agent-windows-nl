@echo off
setlocal EnableExtensions

rem Eenmalig: sentence-transformers model cachen (~90-120 MB) zodat MCP/ingest niet "stil" lijken te hangen.
rem Zelfde conda-detectie als update_knowledge.bat. Zie scripts/rag_pipeline/ACTIVATION.md.
cd /d "%~dp0..\.."
if errorlevel 1 exit /b 1

echo [INFO] Werkmap: %CD%
echo [INFO] Warme start: SentenceTransformer('all-MiniLM-L6-v2') — eerste keer kan even downloaden.

set "HERMES_ACTIVATE_BAT_RESOLVED="
if defined HERMES_ACTIVATE_BAT if exist "%HERMES_ACTIVATE_BAT%" set "HERMES_ACTIVATE_BAT_RESOLVED=%HERMES_ACTIVATE_BAT%"
if not defined HERMES_ACTIVATE_BAT_RESOLVED if defined HERMES_CONDA_ROOT if exist "%HERMES_CONDA_ROOT%\Scripts\activate.bat" (
  set "HERMES_ACTIVATE_BAT_RESOLVED=%HERMES_CONDA_ROOT%\Scripts\activate.bat"
)
if not defined HERMES_ACTIVATE_BAT_RESOLVED if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" (
  set "HERMES_ACTIVATE_BAT_RESOLVED=%USERPROFILE%\miniconda3\Scripts\activate.bat"
)
if not defined HERMES_ACTIVATE_BAT_RESOLVED if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
  set "HERMES_ACTIVATE_BAT_RESOLVED=%USERPROFILE%\anaconda3\Scripts\activate.bat"
)
if not defined HERMES_ACTIVATE_BAT_RESOLVED if exist "%LOCALAPPDATA%\miniconda3\Scripts\activate.bat" (
  set "HERMES_ACTIVATE_BAT_RESOLVED=%LOCALAPPDATA%\miniconda3\Scripts\activate.bat"
)
if not defined HERMES_ACTIVATE_BAT_RESOLVED if exist "%LOCALAPPDATA%\anaconda3\Scripts\activate.bat" (
  set "HERMES_ACTIVATE_BAT_RESOLVED=%LOCALAPPDATA%\anaconda3\Scripts\activate.bat"
)
if not defined HERMES_ACTIVATE_BAT_RESOLVED (
  echo [ERROR] Geen conda Scripts\activate.bat gevonden. Zet HERMES_ACTIVATE_BAT of HERMES_CONDA_ROOT.
  pause
  exit /b 1
)

if not defined HERMES_CONDA_ENV set "HERMES_CONDA_ENV=hermes-env"
echo [INFO] Activeer conda-omgeving %HERMES_CONDA_ENV%...
call "%HERMES_ACTIVATE_BAT_RESOLVED%" %HERMES_CONDA_ENV%
if errorlevel 1 (
  echo [ERROR] Conda-activering mislukt.
  pause
  exit /b 1
)

python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
if errorlevel 1 (
  echo [ERROR] Warme start mislukt ^(exit %ERRORLEVEL%^).
  pause
  exit /b %ERRORLEVEL%
)

echo [OK] Modelcache gehydrateerd — MCP kan nu sneller opstarten.
pause
endlocal
