@echo off

setlocal EnableExtensions

title Hermes RAG - kennis bijwerken

cd /d "%~dp0"

rem Taakbalk/dubbelklik: interactief (J/N + pause). Nacht: gebruik RAG_KNOWLEDGE_UPDATE_NIGHT.bat
set "HERMES_NONINTERACTIVE="

call "%~dp0scripts\update_knowledge.bat" %*

set "RAG_EXIT=%ERRORLEVEL%"

if /i not "%HERMES_NONINTERACTIVE%"=="1" (
  if not "%RAG_EXIT%"=="0" echo [ERROR] RAG exit %RAG_EXIT%
  pause
)

endlocal & exit /b %RAG_EXIT%

