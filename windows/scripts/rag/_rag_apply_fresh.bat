@echo off
rem Wis LanceDB-map als HERMES_RAG_FRESH=j|1|yes (per-domein: HERMES_LANCEDB_PATH moet gezet zijn).
setlocal EnableExtensions EnableDelayedExpansion

set "FRESH=0"
if /i "%HERMES_RAG_FRESH%"=="j" set "FRESH=1"
if /i "%HERMES_RAG_FRESH%"=="1" set "FRESH=1"
if /i "%HERMES_RAG_FRESH%"=="yes" set "FRESH=1"
if /i "%HERMES_RAG_FRESH%"=="true" set "FRESH=1"
if "%FRESH%"=="0" endlocal & exit /b 0

if not defined HERMES_LANCEDB_PATH (
  echo [ERROR] HERMES_LANCEDB_PATH niet gezet — geen fresh-wipe mogelijk.
  endlocal & exit /b 1
)

echo [WARN] Frisse start: database wordt gewist.
echo [WARN] Sluit Hermes/MCP-sessies die LanceDB open hebben.
echo [INFO] Doel: %HERMES_LANCEDB_PATH%

if not exist "%HERMES_LANCEDB_PATH%" (
  echo [INFO] Geen bestaande database-map; overslaan.
  endlocal & exit /b 0
)

call :WipeLanceDb "%HERMES_LANCEDB_PATH%"
endlocal & exit /b %ERRORLEVEL%

:WipeLanceDb
setlocal EnableDelayedExpansion
set "ROOT=%~1"
for %%I in ("!ROOT!") do (
  set "LDB_PARENT=%%~dpI"
  set "LDB_LEAF=%%~nxI"
)
set "LDB_STAGING=!LDB_LEAF!.HERMES_TEMP_WIPE"
pushd "!LDB_PARENT!" 2>nul
if errorlevel 1 (
  echo [ERROR] Kan parentmap niet openen: !LDB_PARENT!
  endlocal & exit /b 1
)
if exist "!LDB_STAGING!" rmdir /s /q "!LDB_STAGING!" 2>nul
ren "!LDB_LEAF!" "!LDB_STAGING!" 2>nul
if errorlevel 1 (
  echo [ERROR] Wissen mislukt — LanceDB in gebruik. Sluit Hermes/MCP en probeer opnieuw.
  popd
  endlocal & exit /b 1
)
rmdir /s /q "!LDB_STAGING!" 2>nul
if errorlevel 1 (
  echo [ERROR] Wissen mislukt — map mogelijk gelocked: !LDB_STAGING!
  popd
  endlocal & exit /b 1
)
popd
endlocal & exit /b 0
