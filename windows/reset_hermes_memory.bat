@echo off
setlocal EnableExtensions
title Hermes Agent - Memory Reset

set "REPO_ROOT=%~dp0.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"

rem --- Genereer echt ESC karakter voor kleuren ---
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"

rem --- ANSI Kleurcodes ---
set "GOUD=%ESC%[93m"
set "CYAAN=%ESC%[96m"
set "GROEN=%ESC%[92m"
set "ROOD=%ESC%[91m"
set "RESET=%ESC%[0m"

rem --- Optioneel: Forceer Windows Terminal voor beste kleur-support ---
if not defined WT_SESSION (
    where wt.exe >nul 2>&1
    if %errorlevel% equ 0 (
        start wt -d "%REPO_ROOT%" cmd /c "\"%~f0\" %*"
        exit /b
    )
)

echo %GOUD%====================================================
echo  Hermes Agent: Memory ^& Cache Reset
echo ====================================================%RESET%
echo.
echo %CYAAN%Dit script wist alle oude chatgeschiedenis, sessies en logs.%RESET%
echo %CYAAN%Je API-sleutels (.env) en configuratie blijven bewaard.%RESET%
echo.
echo %ROOD%LET OP: Sluit de Hermes Agent chat eerst volledig af!%RESET%
echo.
set /p "confirm=Weet je zeker dat je het geheugen wilt wissen? (Y/N): "
if /i "%confirm%" neq "Y" exit /b

set "HERMES_DIR=%USERPROFILE%\.hermes"

echo.
echo %CYAAN%[INFO] Geheugen aan het wissen in %HERMES_DIR%...%RESET%

rem --- Probeer bestanden te verwijderen met foutcontrole ---
del /f /q "%HERMES_DIR%\state.db" 2>nul
if exist "%HERMES_DIR%\state.db" (
    echo %ROOD%[FOUT] Kan state.db niet wissen. Staat Hermes nog open?%RESET%
) else (
    echo %GROEN%[OK] Chatgeschiedenis gewist.%RESET%
)

del /f /q "%HERMES_DIR%\sessions\*.*" 2>nul
del /f /q "%HERMES_DIR%\logs\*.*" 2>nul
del /f /q "%HERMES_DIR%\memories\*.*" 2>nul

echo.
echo %GROEN%====================================================
echo  [SUCCESS] Het geheugen is volledig opgeschoond.
echo ====================================================%RESET%
echo.
pause
