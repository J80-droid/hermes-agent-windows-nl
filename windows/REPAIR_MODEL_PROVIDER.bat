@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo ====================================================
echo  Hermes: model/provider coherence repair
echo ====================================================
echo [INFO] Aligns auth.json active_provider with root config model.provider
echo [INFO] Fixes split-brain (e.g. Nous in auth, Gemini in config)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\repair_model_provider_coherence.ps1"
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo [ERROR] Exit %ERR%
  pause
  exit /b %ERR%
)
echo.
echo Volgende stap: hermes doctor  ^&  hermes config get model.provider
echo.
pause
exit /b 0
