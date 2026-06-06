# Tier A working tree E2E — restore + git clean + drift gate.
param([string]$RepoRoot = '')

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$harness = Join-Path $scriptRoot 'TierAWorkingTreeE2E.harness.py'
if (-not (Test-Path -LiteralPath $harness)) {
    Write-Host '[FAIL] TierAWorkingTreeE2E.harness.py ontbreekt' -ForegroundColor Red
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
