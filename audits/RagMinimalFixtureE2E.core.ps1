# RAG minimal fixture E2E — seed + preflight + ingest smoke.
param([string]$RepoRoot = '')

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$harness = Join-Path $scriptRoot 'RagMinimalFixtureE2E.harness.py'
$python = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }

Push-Location $RepoRoot
try {
    & $python $harness
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
