@echo off
setlocal
cd /d "%~dp0.."
python audits\CodebaseVizSprint4E2E.harness.py
exit /b %ERRORLEVEL%
