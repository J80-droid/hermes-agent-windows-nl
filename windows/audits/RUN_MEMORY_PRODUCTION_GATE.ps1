# Gecombineerde productie-poort: trust limits, memory-architectuur E2E, trust forensic E2E, pytest.
param(
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

. (Join-Path $scriptRoot '..\HermesShellCommon.ps1')

$failures = 0
Write-Host '=== Memory Production Gate ===' -ForegroundColor Cyan

$limitsScript = Join-Path $RepoRoot 'windows\scripts\apply_trust_memory_limits.ps1'
if (Test-Path -LiteralPath $limitsScript) {
    Write-Host '--- apply_trust_memory_limits ---' -ForegroundColor Cyan
    & $limitsScript
    if (Test-NativeCommandFailed) { $failures++ }
} else {
    Write-Host '[FAIL] apply_trust_memory_limits.ps1 ontbreekt' -ForegroundColor Red
    $failures++
}

$memE2e = Join-Path $scriptRoot 'RUN_MEMORY_ARCHITECTURE_E2E.ps1'
Write-Host '--- RUN_MEMORY_ARCHITECTURE_E2E ---' -ForegroundColor Cyan
& $memE2e -RepoRoot $RepoRoot
if (Test-NativeCommandFailed) { $failures++ }

$trustE2e = Join-Path $scriptRoot 'RUN_TRUST_FORENSIC_E2E.ps1'
Write-Host '--- RUN_TRUST_FORENSIC_E2E ---' -ForegroundColor Cyan
& $trustE2e -RepoRoot $RepoRoot
if (Test-NativeCommandFailed) { $failures++ }

$conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
$pytestTargets = @(
    (Join-Path $RepoRoot 'tests\windows\test_trust_forensic_docs.py'),
    (Join-Path $RepoRoot 'tests\tools\test_memory_tool.py')
)
Write-Host '--- pytest memory/trust ---' -ForegroundColor Cyan
if (Test-Path -LiteralPath $conda) {
    & $conda run -n hermes-env --no-capture-output python -m pytest @pytestTargets -q --tb=short 2>&1 | ForEach-Object { Write-Host $_ }
} else {
    $python = if ($env:HERMES_AUDIT_PYTHON) { $env:HERMES_AUDIT_PYTHON } else { 'python' }
    & $python -m pytest @pytestTargets -q --tb=short 2>&1 | ForEach-Object { Write-Host $_ }
}
if (Test-NativeCommandFailed) { $failures++ }

if ($failures -gt 0) {
    Write-Host "=== MEMORY PRODUCTION GATE: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== MEMORY PRODUCTION GATE: PASS ===' -ForegroundColor Green
exit 0
