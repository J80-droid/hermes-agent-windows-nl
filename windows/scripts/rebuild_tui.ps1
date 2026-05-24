# Rebuild ui-tui/dist/entry.js after git pull or TUI source changes.
param(
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'

if (-not $RepoRoot.Trim()) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}

$tuiDir = Join-Path $RepoRoot 'ui-tui'
$pkg = Join-Path $tuiDir 'package.json'
if (-not (Test-Path -LiteralPath $pkg)) {
    Write-Host "[ERROR] Ontbreekt: $pkg" -ForegroundColor Red
    exit 1
}

$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    Write-Host '[ERROR] npm niet op PATH — installeer Node.js of start Hermes opnieuw (herbouwt TUI automatisch).' -ForegroundColor Red
    exit 1
}

Push-Location $tuiDir
try {
    & npm run build --silent
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[ERROR] ui-tui npm run build faalde' -ForegroundColor Red
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host '[OK] ui-tui/dist/entry.js herbouwd — Hermes volledig afsluiten en opnieuw starten.' -ForegroundColor Green
exit 0
