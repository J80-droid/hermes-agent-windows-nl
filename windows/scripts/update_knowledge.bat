@echo off
setlocal EnableExtensions

rem LanceDB RAG: herbouw index vanaf hermes-agent root (ongeacht startlocatie van dit .bat).
rem Institutioneel: zie scripts/rag_pipeline/ACTIVATION.md en windows/INSTITUTIONAL.md (RAG-sectie).
cd /d "%~dp0..\.."

chcp 65001 >nul
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
echo.
echo %ESC%[93m====================================================
echo  Hermes RAG: LanceDB kennisindex bijwerken
echo ====================================================%ESC%[0m
echo [INFO] Werkmap: %CD%

rem Zelfde logica als kb_schema.py: HERMES_LANCEDB_PATH of default %USERPROFILE%\data\my_lancedb.
if defined HERMES_LANCEDB_PATH (
  set "HERMES_LANCEDB=%HERMES_LANCEDB_PATH%"
) else (
  set "HERMES_LANCEDB=%USERPROFILE%\data\my_lancedb"
)

rem Non-interactief: zet HERMES_RAG_FRESH=1/true/yes/j voor wis, 0/n voor behoud (taakplanner/CI).
rem Taakplanner: zet HERMES_NONINTERACTIVE=1 (default N) of expliciet HERMES_RAG_FRESH=0|1.
set "FRISSE_START="
if not defined HERMES_RAG_FRESH if /i "%HERMES_NONINTERACTIVE%"=="1" set "HERMES_RAG_FRESH=0"
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
  echo [WARN] Sluit Hermes en MCP lancedb-knowledge vóór wissen ^(LanceDB-lock^).
  echo [INFO] Oude database wordt verwijderd: "%HERMES_LANCEDB%"
  if exist "%HERMES_LANCEDB%" (
    call :WipeLanceDb "%HERMES_LANCEDB%"
    if errorlevel 1 (
      if /i not "%HERMES_NONINTERACTIVE%"=="1" pause
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
  if /i not "%HERMES_NONINTERACTIVE%"=="1" pause
  exit /b 1
)

if not defined HERMES_CONDA_ENV set "HERMES_CONDA_ENV=hermes-env"
echo [INFO] Activeer conda-omgeving %HERMES_CONDA_ENV%...
call "%HERMES_ACTIVATE_BAT_RESOLVED%" %HERMES_CONDA_ENV%
if errorlevel 1 (
  echo [INFO] Conda-activering mislukt.
  if /i not "%HERMES_NONINTERACTIVE%"=="1" pause
  exit /b 1
)

rem Zelfde pad doorgeven aan Python ^(ingest / kb_schema^) als hierboven gebruikt bij wis.
set "HERMES_LANCEDB_PATH=%HERMES_LANCEDB%"
if not defined HERMES_RAG_RAW_SOURCE set "HERMES_RAG_RAW_SOURCE=%USERPROFILE%\data\raw_source_files"

rem Tesseract OCR ^(UB Mannheim^) voor scan-PDF/PNG; nld via tessdata.
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
  set "PATH=C:\Program Files\Tesseract-OCR;%PATH%"
)
if exist "%USERPROFILE%\Hermes\tessdata\nld.traineddata" (
  rem pytesseract verwacht de map met .traineddata-bestanden, niet de parent Hermes\
  set "TESSDATA_PREFIX=%USERPROFILE%\Hermes\tessdata"
)

rem Institutioneel: safe default, sequentieel, timeouts, UTF-8 log ^(geen UTF-16^).
set "PYTHONUNBUFFERED=1"
set "PYTHONUTF8=1"
if not defined HERMES_RAG_PERF_PROFILE set "HERMES_RAG_PERF_PROFILE=safe"
for /f "delims=" %%L in ('powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0rag_ingest_perf_defaults.ps1" -EmitCmd 2^>nul') do %%L

set "RAG_LOG=%~dp0rag_ingest_run.log"
set "HERMES_RAG_INGEST_LOG=%RAG_LOG%"

echo [RAG-UPDATE] [INFO] Start LanceDB-ingest ^(idempotente upsert per bronbestand^)...
echo [INFO] Bronmap: %HERMES_RAG_RAW_SOURCE%
echo [INFO] Log ^(UTF-8^): %RAG_LOG%
echo [INFO] Live status: %HERMES_LANCEDB%\rag_ingest_live_status.json

rem Ingest via hermes-env ^(conda^) — niet losse powershell-python ^(verkeerde interpreter^).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_rag_ingest.ps1" -LogPath "%RAG_LOG%" -CondaEnv "%HERMES_CONDA_ENV%"
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo [INFO] Ingest eindigde met fout ^(exit %ERR%^).
  if /i not "%HERMES_NONINTERACTIVE%"=="1" pause
  exit /b %ERR%
)

echo [OK] Ingestie-scan afgerond ^(upsert + orphan cleanup + ingest-staat^).
if exist "%HERMES_LANCEDB%\rag_ingest_skipped_report.md" (
  echo [INFO] Overgeslagen PDF/PNG: %HERMES_LANCEDB%\rag_ingest_skipped_report.md
)
if /i not "%HERMES_NONINTERACTIVE%"=="1" pause
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
