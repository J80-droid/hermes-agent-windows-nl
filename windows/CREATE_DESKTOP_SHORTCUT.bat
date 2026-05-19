@echo off
setlocal
rem Canoniek repo-root doorgeven (pyproject.toml) zodat icoon altijd windows\hermes_logo.ico vindt,
rem ook als create_shortcut.ps1 ergens als kopie wordt gestart.
for %%I in ("%~dp0..") do set "HERMES_REPO=%%~fI"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1" -RepoRoot "%HERMES_REPO%"
