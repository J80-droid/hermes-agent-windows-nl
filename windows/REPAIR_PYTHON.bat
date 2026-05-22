@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo ====================================================
echo  Hermes: Python-policy (conda hermes-env)
echo ====================================================
echo [INFO] Kapotte .venv ^(geen pip^) gaat naar .venv.disabled-* 
echo [INFO] RAG/CLI/setup gebruiken conda — niet workspace ^(venv^)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure_hermes_python.ps1" -RepoRoot "%CD%"
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo [ERROR] Exit %ERR%
  pause
  exit /b %ERR%
)
echo.
echo Optioneel conda deps:
echo   conda activate hermes-env
echo   pip install -e ".[rag]"
echo.
pause
exit /b 0
