@echo off
rem Entry voor Windows Terminal (wt -M): terminal reset, dan launch (geen muiscapture op titelbalk).
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -Command ". '%~dp0HermesShellCommon.ps1'; Reset-HermesConsoleInputModes; Invoke-HermesDisableConsoleQuickEdit; try { Clear-Host } catch { }" 2>nul
cls >nul 2>&1
set "HERMES_MAX_FLAG=1"
if defined HERMES_WT_LAUNCH_ARGS (
    call "%~dp0launch_hermes.bat" --maximized !HERMES_WT_LAUNCH_ARGS!
) else (
    call "%~dp0launch_hermes.bat" --maximized
)
endlocal
