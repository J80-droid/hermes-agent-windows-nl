@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul

set "PY=%USERPROFILE%\miniconda3\envs\hermes-env\python.exe"
if not exist "%PY%" set "PY=python"

echo [INFO] Legal fork-skills pytest (gemockte HTTP)...
"%PY%" -m pytest tests\skills\test_rechtspraak_zoeken_skill.py tests\skills\test_uitspraak_parseren_skill.py tests\skills\test_web_research_legal_skill.py -q --tb=short
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo RUN_LEGAL_SKILLS_ROOKTEST: FAIL exit %ERR%
  exit /b %ERR%
)
echo RUN_LEGAL_SKILLS_ROOKTEST: ALL PASS
exit /b 0
