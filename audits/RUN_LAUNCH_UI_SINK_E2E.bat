@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
python audits\LaunchUiSinkE2E.harness.py
exit /b %ERRORLEVEL%
