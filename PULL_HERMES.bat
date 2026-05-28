@echo off
REM Doorverwijzing — gebruik bij voorkeur: start_hermes.bat --pull %*
call "%~dp0start_hermes.bat" --pull %*
exit /b %ERRORLEVEL%
