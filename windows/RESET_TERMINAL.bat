@echo off
rem Muisklik vast / markeermodus — zelfde keten als FIX_MOUSE_BLOCKED + schone herstart.
setlocal EnableExtensions
cd /d "%~dp0.."
set "HERMES_NO_PAUSE=1"
call "%~dp0FIX_MOUSE_BLOCKED.bat"
exit /b %ERRORLEVEL%
