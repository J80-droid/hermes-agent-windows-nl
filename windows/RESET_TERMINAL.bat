@echo off
rem Muisklik vast / markeermodus / oude sessie-resten — eenmalig vóór start_hermes.bat
setlocal EnableExtensions
cd /d "%~dp0.."
set "PY="
if exist "%USERPROFILE%\miniconda3\envs\hermes-env\python.exe" set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\miniconda3\envs\hermes-env\python.exe" set "PY=%LOCALAPPDATA%\miniconda3\envs\hermes-env\python.exe"
echo [INFO] Terminal reset (muismodi, alternate screen)...
if defined PY (
    "%PY%" -c "from hermes_cli.win32_console import release_terminal_capture, configure_interactive_console; release_terminal_capture(); configure_interactive_console()"
) else (
    echo [WARN] hermes-env python niet gevonden — sluit alle cmd/WT-vensters handmatig.
)
echo [INFO] Sluit daarna ALLE Hermes/Windows Terminal-tabbladen en start start_hermes.bat opnieuw.
echo [INFO] Minimaliseren/sluiten: titelbalk van Windows Terminal (niet in het zwarte vlak).
echo [INFO] Muisklik vast in chat? Ctrl+Shift+M = markeermodus uit.
if /I not "%HERMES_NO_PAUSE%"=="1" pause
