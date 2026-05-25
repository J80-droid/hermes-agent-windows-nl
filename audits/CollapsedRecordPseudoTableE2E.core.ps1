# Collapsed record pseudo-table E2E (Component/Keuze/Status + em-dash).
param(
    [string]$RepoRoot = ''
)

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
    $conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
    if (Test-Path -LiteralPath $conda) {
        $out = & $conda run -n hermes-env python -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            return ($out | Select-Object -Last 1).ToString().Trim()
        }
    }
    $fallback = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if (Test-Path -LiteralPath $fallback) { return $fallback }
    return 'python'
}

$harness = Join-Path $scriptRoot 'CollapsedRecordPseudoTableE2E.harness.py'
if (-not (Test-Path -LiteralPath $harness)) {
    Write-Host '[FAIL] CollapsedRecordPseudoTableE2E.harness.py ontbreekt' -ForegroundColor Red
    exit 1
}

$python = Get-HermesAuditPython
Write-Host "=== CollapsedRecordPseudoTableE2E (python: $python) ===" -ForegroundColor Cyan
Push-Location $RepoRoot
try {
    & $python $harness
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
