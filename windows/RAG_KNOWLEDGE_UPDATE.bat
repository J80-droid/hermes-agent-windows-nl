@echo off

setlocal EnableExtensions

title Hermes RAG - kennis bijwerken

cd /d "%~dp0"

call "%~dp0scripts\update_knowledge.bat" %*

set "RAG_EXIT=%ERRORLEVEL%"

endlocal & exit /b %RAG_EXIT%

