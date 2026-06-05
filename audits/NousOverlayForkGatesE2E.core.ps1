# Nous overlay fork gates E2E — launcher (argv, config get, toolset check, legal USER).
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

$harness = Join-Path $scriptRoot 'NousOverlayForkGatesE2E.harness.py'
if (-not (Test-Path -LiteralPath $harness)) {
    Write-Host '[FAIL] NousOverlayForkGatesE2E.harness.py ontbreekt' -ForegroundColor Red
    exit 1
}

$python = Get-HermesAuditPython
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$reportPath = Join-Path $scriptRoot ("NOUS_OVERLAY_FORK_GATES_E2E_REPORT_" + $reportStamp + '.md')
$logPath = Join-Path $scriptRoot ("NOUS_OVERLAY_FORK_GATES_E2E_LOG_" + $reportStamp + '.txt')

Write-Host "=== Nous Overlay Fork Gates E2E (python: $python) ===" -ForegroundColor Cyan
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

$status = if ($exitCode -eq 0) { 'PASS' } else { 'FAIL' }
@"
# Nous Overlay Fork Gates E2E — $status

Generated: $reportStamp
Repo: $RepoRoot
Python: $python

## Scope

- sync_profile_toolsets argv sanitizer + provision --profile
- overlay CLI ``config get`` (argparse + config fork)
- toolset --check skip ``_user_customized.cli``
- legal USER stale-domain strip (sync_profile_memories)
- toolset_domain_e2e_runtime env guard

"@ | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host ''
Write-Host "=== NOUS OVERLAY FORK GATES E2E: $status ===" -ForegroundColor $(if ($exitCode -eq 0) { 'Green' } else { 'Red' })
Write-Host "Report: $reportPath"

if ($exitCode -ne 0) { exit 1 }
exit 0
