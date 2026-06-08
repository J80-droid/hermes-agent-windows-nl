@echo off
setlocal
cd /d "%~dp0\..\.."
python -m ty check .
if errorlevel 1 exit /b 1
exit /b 0
