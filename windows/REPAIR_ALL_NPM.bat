@echo off
rem npm audit fix voor alle Hermes npm-projecten (repo-root workspaces + standalone).
setlocal EnableExtensions
set "REPO=%~dp0.."
set "FAIL=0"

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm niet op PATH
  exit /b 1
)

for %%D in (
  "%REPO%"
  "%REPO%\website"
  "%REPO%\scripts\whatsapp-bridge"
) do (
  if exist "%%~D\package.json" (
    echo.
    echo [INFO] npm audit fix in %%~D
    pushd "%%~D"
    call npm audit fix
    if errorlevel 1 set "FAIL=1"
    popd
  )
)

if not "%FAIL%"=="0" (
  echo [WARN] Een of meer npm audit fix runs faalden — controleer handmatig met npm audit
  exit /b 1
)
echo.
echo [OK] Alle npm audit fixes afgerond
exit /b 0
