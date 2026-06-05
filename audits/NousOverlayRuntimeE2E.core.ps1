# Nous overlay runtime wiring E2E (P0–P5) — launcher.
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

$harness = Join-Path $scriptRoot 'NousOverlayRuntimeE2E.harness.py'
if (-not (Test-Path -LiteralPath $harness)) {
    Write-Host '[FAIL] NousOverlayRuntimeE2E.harness.py ontbreekt' -ForegroundColor Red
    exit 1
}

$python = Get-HermesAuditPython
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$reportPath = Join-Path $scriptRoot ("NOUS_OVERLAY_RUNTIME_E2E_REPORT_" + $reportStamp + '.md')
$logPath = Join-Path $scriptRoot ("NOUS_OVERLAY_RUNTIME_E2E_LOG_" + $reportStamp + '.txt')

Write-Host "=== Nous Overlay Runtime E2E (python: $python) ===" -ForegroundColor Cyan
$env:PYTHONPATH = $RepoRoot
if (-not $env:HERMES_HOME) {
    $env:HERMES_HOME = Join-Path $env:LOCALAPPDATA 'hermes'
}

Push-Location $RepoRoot
try {
    & $python $harness 2>&1 | Tee-Object -FilePath $logPath
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

$status = if ($exitCode -eq 0) { 'PASS' } else { 'FAIL' }
@"
# Nous Overlay Runtime E2E — $status

Generated: $reportStamp
Repo: $RepoRoot
Python: $python

## Scope

- Bootstrap runtime patches (CLI, agent throughput, pricing, models)
- Agent stream/finalize tok/s wiring
- CLI _stream_delta wrap resilience
- /tps and /cost slash dispatch
- Tier A cli.py guard script
- Overlay pytest runtime subset

"@ | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host ''
Write-Host "=== NOUS OVERLAY RUNTIME E2E: $status ===" -ForegroundColor $(if ($exitCode -eq 0) { 'Green' } else { 'Red' })
Write-Host "Report: $reportPath"

if ($exitCode -ne 0) { exit 1 }
exit 0
