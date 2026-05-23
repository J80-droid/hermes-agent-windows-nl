@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo ====================================================
echo  Hermes: na git pull (verify + taakbalk-iconen)
echo ====================================================
echo [INFO] Repo: %CD%
echo.

if exist "%~dp0VERIFY_WINDOWS_CHAIN.bat" (
  call "%~dp0VERIFY_WINDOWS_CHAIN.bat"
) else (
  echo [WARN] VERIFY_WINDOWS_CHAIN.bat ontbreekt
)

echo.
echo [INFO] Trust and Forensic runtime (SOUL + memory, geen scrub)...
set "HERMES_SKIP_PAUSE=1"
call "%~dp0SYNC_TRUST_RUNTIME.bat"
set "HERMES_SKIP_PAUSE="
echo.
echo [INFO] SOUL domein-templates (13 profielen: repo -^> runtime)...
set "HERMES_SKIP_PAUSE=1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_all_domain_souls_from_templates.ps1"
set "HERMES_SKIP_PAUSE="
echo [TIP] Nieuwe chat in Hermes: /new
echo.
echo [INFO] Domein-toolsets (platform_toolsets.cli)...
set "HERMES_SKIP_PAUSE=1"
call "%~dp0SYNC_DOMAIN_TOOLSETS.bat"
set "HERMES_SKIP_PAUSE="
echo.
echo [INFO] Nieuwe skills (bijv. landkaart): hermes update of nieuwe chat-sessie.
echo.
echo [INFO] Taakbalk-.lnk en icooncache vernieuwen...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_hermes_taskbar_pins.ps1" -RepoRoot "%CD%" -Quiet
if errorlevel 1 (
  echo [WARN] fix_hermes_taskbar_pins.ps1 mislukt
) else (
  echo [OK] Taakbalk-snelkoppelingen bijgewerkt.
)

echo.
echo [INFO] Eenmalig bij oud zwart H op UPDATE:
echo   1. Rechtsklik UPDATE-pin - Losmaken van de taakbalk
echo   2. windows\Hermes - update - naar taakbalk slepen.lnk - Vastmaken aan taakbalk
echo      (niet UPDATE_HERMES.bat direct slepen)
echo.
pause
exit /b 0
