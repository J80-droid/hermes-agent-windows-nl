@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\.."
chcp 65001 >nul

set "ESC= "
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
echo %ESC%[96m====================================================
echo  Hermes Agent: MERGE upstream (IDE-guided)
echo ====================================================%ESC%[0m
echo.
echo [INFO] Standaard: merge + IDE-prompt — GEEN blind auto-resolve.
echo        Preview zonder git:  MERGE_UPSTREAM.bat -PromptOnly
echo        Na IDE-fix:          MERGE_UPSTREAM.bat -FinalizeOnly
echo        Blind auto (oude):   MERGE_UPSTREAM.bat -AutoResolve
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0merge_upstream_fork.ps1" %*
set "ERR=!ERRORLEVEL!"
if not "!ERR!"=="0" (
  echo.
  if "!ERR!"=="7" (
    echo [INFO] Conflicten open — IDE-prompt staat in %%LOCALAPPDATA%%\hermes\merge_prompts\
    echo        Plak in Cursor, fix, git add, dan: MERGE_UPSTREAM.bat -FinalizeOnly
  ) else (
    echo [ERROR] Merge keten gestopt met code !ERR!
    echo [INFO] Zie windows\UPSTREAM_SYNC.md
  )
  pause
  exit /b !ERR!
)

echo.
echo [OK] Merge + update keten geslaagd.
if "%HERMES_SKIP_PAUSE_AFTER_UPDATE%"=="1" goto :eof
pause
exit /b 0
