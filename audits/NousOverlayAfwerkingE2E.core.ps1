# Nous overlay afwerking E2E — dedup, trust preflight, bootstrap wiring.
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

$harness = Join-Path $scriptRoot 'NousOverlayAfwerkingE2E.harness.py'
if (-not (Test-Path -LiteralPath $harness)) {
    Write-Host '[FAIL] NousOverlayAfwerkingE2E.harness.py ontbreekt' -ForegroundColor Red
    exit 1
}

$python = Get-HermesAuditPython
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$reportPath = Join-Path $scriptRoot ("NOUS_OVERLAY_AFWERKING_E2E_REPORT_" + $reportStamp + '.md')
$logPath = Join-Path $scriptRoot ("NOUS_OVERLAY_AFWERKING_E2E_LOG_" + $reportStamp + '.txt')

Write-Host "=== Nous Overlay Afwerking E2E (python: $python) ===" -ForegroundColor Cyan
$env:PYTHONPATH = $RepoRoot
Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue

Push-Location $RepoRoot
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    & $python $harness 2>&1 | Tee-Object -FilePath $logPath
    $exitCode = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $prevEap
    Pop-Location
}

if ($exitCode -ne 0) {
    Write-Host '=== NOUS OVERLAY AFWERKING E2E: FAIL ===' -ForegroundColor Red
    exit $exitCode
}

@"
# Nous Overlay Afwerking E2E — PASS

Generated: $reportStamp
Repo: $RepoRoot
Python: $python
Log: $logPath
"@ | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host "=== NOUS OVERLAY AFWERKING E2E: PASS ===" -ForegroundColor Green
Write-Host "Report: $reportPath"
exit 0
