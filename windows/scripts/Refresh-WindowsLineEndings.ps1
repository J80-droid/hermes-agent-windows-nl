# Eenmalig/herhaal: werkmap schoon na CRLF/LF-mismatch (core.autocrlf=false + .gitattributes).
# Normaliseert windows/*.bat|ps1|cmd volgens .gitattributes; commit daarna de staged wijzigingen.
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location -LiteralPath $repoRoot

git add --renormalize `
    windows/ `
    scripts/windows/ `
    audits/RUN_DASHBOARD_WS_DEV.bat `
    audits/RUN_FULL_VERIFICATION.ps1 `
    tests/windows/test_hermes_python_institutional.py `
    tests/windows/test_launch_dashboard_on_start.py

Write-Host 'Gestaged: line-ending normalisatie. Controleer met: git diff --cached -w --stat' -ForegroundColor Cyan
git status -sb
