@echo off
rem Back-compat wrapper — repareert alle npm-projecten (zie REPAIR_ALL_NPM.bat).
call "%~dp0REPAIR_ALL_NPM.bat" %*
exit /b %ERRORLEVEL%
