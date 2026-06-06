@echo off
rem Alias: snelkoppelingen. Zie HERMES_ONDERHOUD.bat -ShortcutsOnly
cd /d "%~dp0\.."
call "%~dp0HERMES_ONDERHOUD.bat" -ShortcutsOnly %*
exit /b %ERRORLEVEL%
