# Institutional P0+P1 wiring E2E (bat paths, geen live ingest/chat).
param([string]$RepoRoot = '')

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

function Get-HermesAuditPython {
    if ($env:HERMES_AUDIT_PYTHON -and (Test-Path -LiteralPath $env:HERMES_AUDIT_PYTHON)) {
        return $env:HERMES_AUDIT_PYTHON
    }
    $fallback = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if (Test-Path -LiteralPath $fallback) { return $fallback }
    return 'python'
}

$harness = Join-Path $scriptRoot 'InstitutionalP0P1WiringE2E.harness.py'
$python = Get-HermesAuditPython
Write-Host "=== InstitutionalP0P1WiringE2E (python: $python) ===" -ForegroundColor Cyan
Push-Location $RepoRoot
& $python $harness
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { exit $code }
Write-Host 'RUN_INSTITUTIONAL_P0P1_WIRING_E2E: ALL PASS' -ForegroundColor Green
exit 0
