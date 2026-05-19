@echo off
setlocal EnableExtensions

rem LanceDB RAG: herbouw index vanaf hermes-agent root (ongeacht startlocatie van dit .bat).
rem Institutioneel: zie scripts/rag_pipeline/ACTIVATION.md en windows/INSTITUTIONAL_OPTION1.md (RAG-sectie).
cd /d "%~dp0..\.."

echo [INFO] Werkmap: %CD%

rem Zelfde logica als kb_schema.py: HERMES_LANCEDB_PATH of default %USERPROFILE%\data\my_lancedb.
if defined HERMES_LANCEDB_PATH (
  set "HERMES_LANCEDB=%HERMES_LANCEDB_PATH%"
) else (
  set "HERMES_LANCEDB=%USERPROFILE%\data\my_lancedb"
)

rem Non-interactief: zet HERMES_RAG_FRESH=1/true/yes/j voor wis, 0/n voor behoud (taakplanner/CI).
set "FRISSE_START="
if defined HERMES_RAG_FRESH (
  echo [INFO] HERMES_RAG_FRESH=%HERMES_RAG_FRESH% ^(non-interactief^)
  if /i "%HERMES_RAG_FRESH%"=="1" set "FRISSE_START=J"
  if /i "%HERMES_RAG_FRESH%"=="true" set "FRISSE_START=J"
  if /i "%HERMES_RAG_FRESH%"=="yes" set "FRISSE_START=J"
  if /i "%HERMES_RAG_FRESH%"=="j" set "FRISSE_START=J"
  if /i "%HERMES_RAG_FRESH%"=="0" set "FRISSE_START=N"
  if /i "%HERMES_RAG_FRESH%"=="n" set "FRISSE_START=N"
  if /i "%HERMES_RAG_FRESH%"=="no" set "FRISSE_START=N"
  if not defined FRISSE_START set "FRISSE_START=N"
) else (
  rem ANSI-escape helper (werkt in Windows 10+ Terminal en moderne CMD)
  for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
  echo.
  echo %ESC%[36mDatabase keuze:%ESC%[0m
  echo %ESC%[92m  J = Ja  %ESC%[0m- Wis ALLES en indexeer opnieuw (frisse start)
  echo %ESC%[93m  N = Nee %ESC%[0m- Alleen nieuwe/gewijzigde bestanden (snel)
  echo.
  set /p FRISSE_START="Kies J of N: "
)

if /i "%FRISSE_START%"=="J" (
  echo [INFO] Oude database wordt verwijderd: "%HERMES_LANCEDB%"
  if exist "%HERMES_LANCEDB%" (
    call :WipeLanceDb "%HERMES_LANCEDB%"
    if errorlevel 1 (
      pause
      exit /b 1
    )
  ) else (
    echo [INFO] Geen bestaande database-map; overslaan verwijderen.
  )
) else (
  echo [RAG-UPDATE] [INFO] Idempotente upsert gestart ^(bestaande chunks worden overschreven, nieuwe toegevoegd^)...
)

rem Conda: HERMES_ACTIVATE_BAT ^(volledig pad^) of HERMES_CONDA_ROOT ^(installatiemap^); anders gangbare locaties.
set "HERMES_ACTIVATE_BAT_RESOLVED="
if defined HERMES_ACTIVATE_BAT if exist "%HERMES_ACTIVATE_BAT%" set "HERMES_ACTIVATE_BAT_RESOLVED=%HERMES_ACTIVATE_BAT%"
if not defined HERMES_ACTIVATE_BAT_RESOLVED if defined HERMES_CONDA_ROOT if exist "%HERMES_CONDA_ROOT%\Scripts\activate.bat" (
  set "HERMES_ACTIVATE_BAT_RESOLVED=%HERMES_CONDA_ROOT%\Scripts\activate.bat"
)
if not defined HERMES_ACTIVATE_BAT_RESOLVED if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" (
  set "HERMES_ACTIVATE_BAT_RESOLVED=%USERPROFILE%\miniconda3\Scripts\activate.bat"
)
if not defined HERMES_ACTIVATE_BAT_RESOLVED if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
  set "HERMES_ACTIVATE_BAT_RESOLVED=%USERPROFILE%\anaconda3\Scripts\activate.bat"
)
if not defined HERMES_ACTIVATE_BAT_RESOLVED if exist "%LOCALAPPDATA%\miniconda3\Scripts\activate.bat" (
  set "HERMES_ACTIVATE_BAT_RESOLVED=%LOCALAPPDATA%\miniconda3\Scripts\activate.bat"
)
if not defined HERMES_ACTIVATE_BAT_RESOLVED if exist "%LOCALAPPDATA%\anaconda3\Scripts\activate.bat" (
  set "HERMES_ACTIVATE_BAT_RESOLVED=%LOCALAPPDATA%\anaconda3\Scripts\activate.bat"
)
if not defined HERMES_ACTIVATE_BAT_RESOLVED (
  echo [ERROR] Geen conda Scripts\activate.bat gevonden.
  echo        Zet machine-breed HERMES_ACTIVATE_BAT of HERMES_CONDA_ROOT, of installeer Miniconda/Anaconda op een standaardlocatie.
  pause
  exit /b 1
)

if not defined HERMES_CONDA_ENV set "HERMES_CONDA_ENV=hermes-env"
echo [INFO] Activeer conda-omgeving %HERMES_CONDA_ENV%...
call "%HERMES_ACTIVATE_BAT_RESOLVED%" %HERMES_CONDA_ENV%
if errorlevel 1 (
  echo [INFO] Conda-activering mislukt.
  pause
  exit /b 1
)

rem Zelfde pad doorgeven aan Python ^(ingest / kb_schema^) als hierboven gebruikt bij wis.
set "HERMES_LANCEDB_PATH=%HERMES_LANCEDB%"

echo [RAG-UPDATE] [INFO] Start LanceDB-ingest ^(idempotente upsert per bronbestand^)...
echo [INFO] Start ingest: python scripts\rag_pipeline\ingest.py
python scripts\rag_pipeline\ingest.py
if errorlevel 1 (
  echo [INFO] Ingest eindigde met fout ^(exit %ERRORLEVEL%^).
  pause
  exit /b %ERRORLEVEL%
)

echo [OK] Ingest afgerond.
pause
endlocal
goto :EOF

rem Hernoem database-map eerst ^(Windows blokkeert rename bij open handles^); daarna rmdir op staging-naam.
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
  echo [ERROR] Kan de parentmap van de database niet openen: !LDB_PARENT!
  endlocal
  exit /b 1
)
if exist "!LDB_STAGING!" rmdir /s /q "!LDB_STAGING!" 2>nul
ren "!LDB_LEAF!" "!LDB_STAGING!" 2>nul
if errorlevel 1 (
  echo [ERROR] Verwijderen mislukt. De database is waarschijnlijk in gebruik door een actieve Hermes- of MCP-sessie. Sluit deze sessies en probeer het opnieuw.
  popd
  endlocal
  exit /b 1
)
rmdir /s /q "!LDB_STAGING!" 2>nul
if errorlevel 1 (
  echo [ERROR] Verwijderen mislukt. De database is waarschijnlijk in gebruik door een actieve Hermes- of MCP-sessie. Sluit deze sessies en probeer het opnieuw.
  echo [WARN] Map staat mogelijk als !LDB_STAGING! in !LDB_PARENT! — ruim handmatig op na sluiten van sessies.
  popd
  endlocal
  exit /b 1
)
popd
endlocal
exit /b 0
