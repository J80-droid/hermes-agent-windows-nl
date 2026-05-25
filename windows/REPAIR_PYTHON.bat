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
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure_hermes_python.ps1" -RepoRoot "%CD%" -SyncIde
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo [ERROR] Exit %ERR%
  pause
  exit /b %ERR%
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\check_hermes_rag_after_repair.ps1" -RepoRoot "%CD%"
echo.
echo RAG-deps: vereist voor kennisbank; automatisch bij start/setup via install_rag_extras.ps1
echo   Handmatig: powershell -File windows\scripts\install_rag_extras.ps1
echo.
pause
exit /b 0
