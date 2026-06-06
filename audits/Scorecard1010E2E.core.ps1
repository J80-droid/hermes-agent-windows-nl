# Scorecard 10/10 E2E — Tier A hygiene, pytest helpers, RAG seed wiring.
param([string]$RepoRoot = '')

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$harness = Join-Path $scriptRoot 'Scorecard1010E2E.harness.py'
if (-not (Test-Path -LiteralPath $harness)) {
    Write-Host '[FAIL] Scorecard1010E2E.harness.py ontbreekt' -ForegroundColor Red
    exit 1
}

$python = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }

Push-Location $RepoRoot
try {
    & $python $harness
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
