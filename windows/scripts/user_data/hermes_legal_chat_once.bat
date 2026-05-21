@echo off
setlocal EnableExtensions
set "HERMES_YOLO_MODE=1"
set "HERMES_ACCEPT_HOOKS=1"
call "%~dp0hermes_with_env.bat" -p legal chat -q "Voer search_knowledge uit op actieve zorgplicht P-Direkt en citeer met [Bron: bestandsnaam]." -t mcp -Q --yolo --max-turns 12
exit /b %ERRORLEVEL%
