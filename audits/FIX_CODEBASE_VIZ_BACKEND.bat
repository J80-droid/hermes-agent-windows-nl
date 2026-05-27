@echo off
REM Verouderd alias — alles zit in RUN_DASHBOARD_WS_DEV.bat
echo Gebruik:  audits\RUN_DASHBOARD_WS_DEV.bat
echo.
echo Dat script regelt automatisch:
echo   - Hermes-venv + pip install -e .[web]  (fastapi/uvicorn)
echo   - HERMES_BUNDLED_PLUGINS naar deze repo
echo   - oude user-plugins naar .bak
echo   - dashboard stop + start
call "%~dp0RUN_DASHBOARD_WS_DEV.bat"
