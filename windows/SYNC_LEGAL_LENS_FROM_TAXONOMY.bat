@echo off
REM Sync juridische lenzen-tabel: docs\LEGAL_TAXONOMY.md -> template + runtime legal\SOUL.md
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_legal_lens_from_taxonomy.ps1" %*
exit /b %ERRORLEVEL%
