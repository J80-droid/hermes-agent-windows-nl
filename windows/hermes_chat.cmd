@echo off
setlocal EnableExtensions EnableDelayedExpansion
rem Interactieve Hermes-chat in dezelfde cmd-console (Win32 / prompt_toolkit-safe).
set "WIN_DIR=%~dp0"
for %%I in ("%WIN_DIR%..") do set "REPO_ROOT=%%~fI"
set "ERROR_LOG=%REPO_ROOT%\hermes_last_error.log"
set "STATE_FILE=%TEMP%\hermes_launch_state.cmd"

if not exist "%STATE_FILE%" (
    echo [ERROR] Launch state ontbreekt: %STATE_FILE%
    echo [%DATE% %TIME%] ERROR: hermes_launch_state.cmd missing >> "%ERROR_LOG%" 2>nul
    exit /b 1
)

call "%STATE_FILE%"
if not defined HERMES_PYTHON (
    echo [ERROR] HERMES_PYTHON niet gezet in launch state.
    exit /b 1
)
if not exist "!HERMES_PYTHON!" (
    echo [ERROR] Python niet gevonden: !HERMES_PYTHON!
    exit /b 1
)

set "TERM="
set "COLORTERM="
rem Schone console (geen oude "Session ended" + pause-resten boven nieuwe chat).
cls >nul 2>&1
rem Terminal reset: muismodi + alternate screen los (voorkomt vast muisklik).
"!HERMES_PYTHON!" -c "import sys;s=sys.stdout;s.write('\x1b[?1006l\x1b[?1003l\x1b[?1002l\x1b[?1000l\x1b[?1004l\x1b[?2004l\x1b[?1049l\x1b[<u\x1b[>4m\x1b[0m\x1b[?25h');s.flush()" 2>nul
"!HERMES_PYTHON!" -c "from hermes_cli.win32_console import release_terminal_capture; release_terminal_capture()" 2>nul
chcp 65001 >nul
rem Geen mode con: lines=9000 — lege bufferregels geven zwart scherm bij PgDn/scroll.
if /I "%OS%"=="Windows_NT" "!HERMES_PYTHON!" -c "from hermes_cli.win32_console import configure_interactive_console, align_win32_viewport_to_bottom; configure_interactive_console(); align_win32_viewport_to_bottom()" >nul 2>&1
set "PYTHONIOENCODING=utf-8"
if defined NO_COLOR set "NO_COLOR="
if /I "!FORCE_COLOR!"=="0" set "FORCE_COLOR=1"

cd /d "!HERMES_REPO_ROOT!"
if not defined HERMES_SKIP_HARDWARE_PROBE set "HERMES_SKIP_HARDWARE_PROBE=1"
if not defined HERMES_NO_WAKE_LOCAL_LLM set "HERMES_NO_WAKE_LOCAL_LLM=1"
if not defined HERMES_CHAT_MODE set "HERMES_CHAT_MODE=chat"

set "CHAT_EXIT=0"
if /I "!HERMES_CHAT_MODE!"=="setup" goto :run_setup
if /I "!HERMES_CHAT_MODE!"=="setup_then_chat" goto :run_setup_then_chat
goto :run_chat

:run_setup
call :run_python setup
set "CHAT_EXIT=!ERRORLEVEL!"
goto :done

:run_setup_then_chat
call :run_python setup
if !ERRORLEVEL! neq 0 set "CHAT_EXIT=!ERRORLEVEL!" & goto :done
call :run_python
set "CHAT_EXIT=!ERRORLEVEL!"
goto :done

:run_chat
call :run_python
set "CHAT_EXIT=!ERRORLEVEL!"
goto :done

:run_python
if "%~1"=="" goto :run_main
"!HERMES_PYTHON!" -m hermes_cli.main %~1 !HERMES_CLI_ARG_TAIL!
exit /b %ERRORLEVEL%

:run_main
"!HERMES_PYTHON!" -m hermes_cli.main !HERMES_CLI_ARG_TAIL!
exit /b %ERRORLEVEL%

:done
"!HERMES_PYTHON!" -c "from hermes_cli.win32_console import release_terminal_capture; release_terminal_capture()" 2>nul
if !CHAT_EXIT! neq 0 (
    echo [%DATE% %TIME%] Hermes chat exit !CHAT_EXIT! >> "%ERROR_LOG%"
    echo [ERROR] Hermes chat exit !CHAT_EXIT! — zie hermes_runtime.log >> "%ERROR_LOG%"
)
exit /b !CHAT_EXIT!
