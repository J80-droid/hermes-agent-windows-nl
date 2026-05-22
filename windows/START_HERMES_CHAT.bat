@echo off
rem Eén paneel: authentieke Hermes-chat (geen split log). Zie start_hermes.bat op repo-root.
cd /d "%~dp0\.."
call "%~dp0..\start_hermes.bat" %*
exit /b %ERRORLEVEL%
