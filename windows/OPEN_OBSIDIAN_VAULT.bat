@echo off
rem Hermes Knowledge (Obsidian L4-vault) openen — sync env, scaffold, start Obsidian.
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
title Hermes - Obsidian vault

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\open_obsidian_vault.ps1" -RepoRoot "%CD%" %*
set "RC=%ERRORLEVEL%"
if %RC% neq 0 (
  if not "%HERMES_SKIP_PAUSE%"=="1" pause
  exit /b %RC%
)
exit /b 0
