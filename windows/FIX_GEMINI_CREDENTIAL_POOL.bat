@echo off
rem Herstel kapotte Gemini credential_pool entries (bv. manual "N" in profiles\core\auth.json)
setlocal EnableExtensions
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_gemini_credential_pool.ps1"
exit /b %ERRORLEVEL%
