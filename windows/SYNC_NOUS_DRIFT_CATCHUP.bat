@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Invoke-SyncNousDriftCatchUp.ps1" -RepoRoot "%CD%" %*
exit /b %ERRORLEVEL%
