@echo off
setlocal EnableExtensions
rem Stel standaard launch-profiel in (minimal|full) voor alle start_hermes.bat zonder vlag.
rem Gebruik:  set_launch_profile.bat minimal   |   set_launch_profile.bat full
if "%~1"=="" (
  echo Gebruik: %~nx0 minimal ^| full
  echo Huidige voorkeur:
  powershell -NoProfile -ExecutionPolicy Bypass -Command ". '%~dp0launch_profiles.ps1'; $p = Get-HermesLaunchProfileFromPreferenceFile; if ($p) { Write-Host $p } else { Write-Host '(geen — default minimal)' }"
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command ". '%~dp0launch_profiles.ps1'; Set-HermesLaunchProfilePreference -Profile '%~1'"
if errorlevel 1 (
  echo [ERROR] Ongeldig profiel. Kies: minimal of full
  exit /b 1
)
echo [OK] Standaard launch-profiel: %~1
echo       Opgeslagen in %%LOCALAPPDATA%%\hermes\preferences\launch_profile
exit /b 0
