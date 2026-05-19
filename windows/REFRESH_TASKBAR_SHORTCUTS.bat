@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo ====================================================
echo  Hermes: taakbalk-snelkoppelingen in windows\
echo ====================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_taskbar_shortcuts.ps1" -RepoRoot "%CD%"
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo [ERROR] Exit %ERR%
  pause
  exit /b %ERR%
)
echo.
echo O.a. Start Hermes, Backup, Herstel lokale bestanden, Update, RAG kennis bijwerken — sleep de .lnk uit windows\ naar de taakbalk.
pause
exit /b 0
