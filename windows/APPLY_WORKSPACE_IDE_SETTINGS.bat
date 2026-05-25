@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo ====================================================
echo  Hermes: parent workspace IDE (PSES)
echo ====================================================
echo [INFO] Schrijft Hermes_agent_WS\.vscode\settings.json
echo [INFO] Daarna in Cursor: Reload Window + Restart PowerShell Session
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Apply-HermesWorkspaceIdeSettings.ps1" -WorkspaceRoot "%~dp0..\.."
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo [ERROR] Exit %ERR%
  pause
  exit /b %ERR%
)
echo.
echo [OK] Workspace IDE settings toegepast.
echo [WARN] Voer nog uit in Cursor: Developer: Reload Window
echo [WARN] Daarna: PowerShell: Restart Session
pause
exit /b 0
