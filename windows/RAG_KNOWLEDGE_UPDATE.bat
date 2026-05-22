@echo off

setlocal EnableExtensions

title Hermes RAG - kennis bijwerken

cd /d "%~dp0"

rem Taakbalk/dubbelklik: interactief (J/N + pause). Nacht: gebruik RAG_KNOWLEDGE_UPDATE_NIGHT.bat
set "HERMES_NONINTERACTIVE="

call "%~dp0scripts\update_knowledge.bat" %*

set "RAG_EXIT=%ERRORLEVEL%"

endlocal & exit /b %RAG_EXIT%

