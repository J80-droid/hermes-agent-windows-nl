@echo off
rem Alleen geplande nacht-runs: incrementeel, geen J/N, geen pause.
rem Dagelijks/handmatig: gebruik RAG_KNOWLEDGE_UPDATE.bat (J/N + venster blijft open).
setlocal EnableExtensions

title Hermes RAG - nacht (non-interactive)

cd /d "%~dp0"
call "%~dp0scripts\rag\_rag_apply_institutional_env.bat"
set "HERMES_NONINTERACTIVE=1"
if not defined HERMES_RAG_FRESH set "HERMES_RAG_FRESH=n"

call "%~dp0scripts\update_knowledge.bat" %*

set "RAG_EXIT=%ERRORLEVEL%"
endlocal & exit /b %RAG_EXIT%
