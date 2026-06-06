@echo off
rem Optionele fix voor doctor-waarschuwing "agent-browser npm vulnerabilities".
setlocal EnableExtensions
cd /d "%~dp0.."
if not exist "package.json" (
  echo [ERROR] package.json ontbreekt in %CD%
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm niet op PATH
  exit /b 1
)
echo [INFO] npm audit fix in %CD% ...
call npm audit fix
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo [WARN] npm audit fix exit %ERR% — controleer handmatig: npm audit
  exit /b %ERR%
)
echo [OK] npm audit fix afgerond
exit /b 0
