@echo off
setlocal
cd /d "%~dp0"
if not exist "%USERPROFILE%\.hermes\_local_assets" (
    echo [FOUT] Geen lokale backup in %USERPROFILE%\.hermes\_local_assets
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0restore_local_assets.ps1"
exit /b %ERRORLEVEL%
