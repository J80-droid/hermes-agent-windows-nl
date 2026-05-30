@echo off
REM Eénmalig: map met stabiele Hermes-.lnk voor taakbalk (niet uit windows\ of backups\ slepen).
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_hermes_taskbar_pins.ps1" -PostUpdateGuidance -OpenStableFolder
pause
