@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
echo ====================================================
echo  Hermes: taakbalk-pop-up eenmalig oplossen
echo ====================================================
echo.
echo [INFO] Stap 1: snelkoppelingen bijwerken...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_hermes_taskbar_pins.ps1" -RepoRoot "%CD%"
if errorlevel 1 (
  echo [ERROR] fix_hermes_taskbar_pins mislukt
  pause
  exit /b 1
)
echo.
echo [INFO] Stap 2: test ELKE Hermes-pin op je taakbalk.
echo        Zie je deze pop-up?  Klik JA op die pin ^(verwijdert alleen de dode pin^).
echo        Herhaal tot geen pop-up meer komt.
echo.
echo [INFO] Stap 3: opnieuw vastzetten ^(rechtsklik, niet slepen^):
echo        windows\Start Hermes - naar taakbalk slepen.lnk
echo        of een andere rol uit windows\
echo.
echo [INFO] Verkenner-snelkoppelingen blijven in windows\ werken zoals nu.
echo        Vastzetten via rechtsklik -^> Vastmaken aan taakbalk.
echo.
pause
exit /b 0
