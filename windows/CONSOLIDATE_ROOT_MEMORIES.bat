@echo off
rem Migreer legacy %LOCALAPPDATA%\hermes\memories\ naar profielen; reset root naar seed.
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - Root memory consolidatie

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Invoke-RepairProfileMemoryLimits.ps1" -RepoRoot "%CD%" -Full %*
set "RC=%ERRORLEVEL%"
if %RC% neq 0 pause
exit /b %RC%
