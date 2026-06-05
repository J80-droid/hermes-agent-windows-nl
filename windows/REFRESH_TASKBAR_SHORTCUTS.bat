@echo off
rem Alias: volledig onderhoud (snelkoppelingen + dashboard). Zie HERMES_ONDERHOUD.bat.
cd /d "%~dp0\.."
call "%~dp0HERMES_ONDERHOUD.bat" -ShortcutsOnly %*
exit /b %ERRORLEVEL%
