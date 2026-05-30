@echo off
rem WT titelbalk / muisklik overlay — pytest contract + handmatige checklist (geen live UI-automation).
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "ERR=0"

echo [1/2] pytest mouse overlay contracts...
python -m pytest tests\windows\test_launch_dashboard_on_start.py::test_mouse_regression_contracts tests\windows\test_launch_dashboard_on_start.py::test_expand_console_to_work_area_guarded_in_wt tests\windows\test_launch_dashboard_on_start.py::test_cli_align_viewport_skipped_in_wt -q --tb=short
if errorlevel 1 set "ERR=1"

echo.
echo [2/2] Handmatige verificatie (verplicht voor productie):
echo   1. Sluit ALLE Hermes / cmd / WT-tabbladen.
echo   2. windows\FIX_MOUSE_BLOCKED.bat of windows\RESET_TERMINAL.bat
echo   3. start_hermes.bat — titel moet Windows Terminal zijn.
echo   4. Klik minimize / maximize / close op de WT-titelbalk (niet zwart chatvlak).
echo   5. Chat vast? Ctrl+Shift+M (markeermodus uit).
echo   6. Optioneel isolatie: set HERMES_SKIP_DASHBOARD_ON_START=1 ^& start_hermes.bat
echo   7. Documentatie: windows\MOUSE_OVERLAY_FIX.md
echo.

if "%ERR%"=="1" (
    echo [FAIL] Automatische contract-tests mislukt.
    exit /b 1
)
echo [OK] Automatische contract-tests geslaagd. Voer handmatige stappen 1-7 uit.
exit /b 0
