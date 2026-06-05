# Nous 100% intact + dunne overlay — institutionele E2E (Tier A drift + runtime overlay).
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

$failures = 0
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'

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

function Add-Step {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    if ($Ok) {
        Write-Host ('[OK] ' + $Name + $(if ($Detail) { ' - ' + $Detail } else { '' })) -ForegroundColor Green
    } else {
        Write-Host ('[FAIL] ' + $Name + $(if ($Detail) { ' - ' + $Detail } else { '' })) -ForegroundColor Red
        $script:failures++
    }
}

function Invoke-AuditExe {
    param(
        [string]$Exe,
        [string[]]$ArgumentList = @()
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $Exe @ArgumentList 2>&1 | ForEach-Object { if ("$_") { Write-Host $_ } }
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEap
    return $ok
}

Write-Host '=== Nous Overlay Institutional E2E ===' -ForegroundColor Cyan
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

# 1/8 SYNC_NOUS launcher + core present
$syncBat = Join-Path $RepoRoot 'windows/audits/RUN_SYNC_NOUS_E2E.bat'
$syncCore = Join-Path $RepoRoot 'windows/audits/SYNC_NOUS_E2E.core.ps1'
Add-Step '1/8 SYNC_NOUS E2E entrypoints' (
    (Test-Path -LiteralPath $syncBat) -and (Test-Path -LiteralPath $syncCore)
)

# 2/8 Tier A strict drift
$driftPs1 = Join-Path $RepoRoot 'windows/scripts/Test-NousTreeIdentical.ps1'
$driftOk = Invoke-AuditExe -Exe 'powershell' -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass',
    '-File', $driftPs1, '-RepoRoot', $RepoRoot
)
Add-Step '2/8 Test-NousTreeIdentical (strict)' -Ok $driftOk

# 3/8 Python harness (overlay runtime + Tier A untouched)
$harness = Join-Path $scriptRoot 'NousOverlayInstitutionalE2E.harness.py'
$harnessOk = $false
if (Test-Path -LiteralPath $harness) {
    Push-Location $RepoRoot
    try {
        $harnessOk = Invoke-AuditExe -Exe $python -ArgumentList @($harness)
    } finally {
        Pop-Location
    }
} else {
    Write-Host '[FAIL] NousOverlayInstitutionalE2E.harness.py ontbreekt' -ForegroundColor Red
    $failures++
}
if (Test-Path -LiteralPath $harness) {
    Add-Step '3/8 overlay runtime harness' -Ok $harnessOk -Detail $python
}

# 4/8 verify_usage_cost_bar
$verifyPy = Join-Path $RepoRoot 'scripts/verify_usage_cost_bar.py'
$verifyOk = $false
if (Test-Path -LiteralPath $verifyPy) {
    $verifyOk = Invoke-AuditExe -Exe $python -ArgumentList @($verifyPy, '--verify')
}
Add-Step '4/8 verify_usage_cost_bar' -Ok $verifyOk

# 5/8 classic CLI smoke
$smokePy = Join-Path $RepoRoot 'scripts/status_bar_cost_classic_cli_smoke.py'
$smokeOk = $false
if (Test-Path -LiteralPath $smokePy) {
    $smokeOk = Invoke-AuditExe -Exe $python -ArgumentList @($smokePy)
}
Add-Step '5/8 classic CLI status bar smoke' -Ok $smokeOk

# 6/8 live smoke
$livePy = Join-Path $RepoRoot 'scripts/status_bar_cost_classic_cli_live_smoke.py'
$liveOk = $false
if (Test-Path -LiteralPath $livePy) {
    $liveOk = Invoke-AuditExe -Exe $python -ArgumentList @($livePy)
}
Add-Step '6/8 classic CLI live smoke' -Ok $liveOk

# 7/8 pytest subset (overlay paths)
$pytestOk = Invoke-AuditExe -Exe $python -ArgumentList @(
    '-m', 'pytest',
    (Join-Path $RepoRoot 'tests/hermes_cli/test_status_bar_cost.py'),
    (Join-Path $RepoRoot 'tests/hermes_cli/test_usage_snapshot.py'),
    '-q', '-o', 'addopts=',
    '-k', 'gemini_35 or format_status_bar or resolve_status_bar'
)
Add-Step '7/8 pytest status_bar_cost + usage_snapshot' -Ok $pytestOk

# 8/8 overlay scripts pass verify_windows path-literal policy
$chainPs1 = Join-Path $RepoRoot 'windows/verify_windows_script_chain.ps1'
$chainOk = $false
if (Test-Path -LiteralPath $chainPs1) {
    $env:HERMES_NONINTERACTIVE = '1'
    $chainOk = Invoke-AuditExe -Exe 'powershell' -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $chainPs1, '-RepoRoot', $RepoRoot
    )
}
Add-Step '8/8 verify_windows_script_chain' -Ok $chainOk

# 9/9 optional ui-tui vitest (statusBarThroughput / usageCostBar)
$vitestOk = $true
$uiTui = Join-Path $RepoRoot 'ui-tui'
$copyPs1 = Join-Path $RepoRoot 'windows/scripts/Invoke-CopyHermesOverlaySources.ps1'
if ((Test-Path -LiteralPath $copyPs1)) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $copyPs1 -RepoRoot $RepoRoot -Target ui-tui -Force | Out-Null
}
if ((Get-Command npm -ErrorAction SilentlyContinue) -and (Test-Path -LiteralPath (Join-Path $uiTui 'package.json'))) {
    Push-Location $uiTui
    try {
        $vitestOk = Invoke-AuditExe -Exe 'npx' -ArgumentList @(
            'vitest', 'run',
            'src/domain/statusBarThroughput.test.ts',
            'src/domain/usageCostBar.test.ts',
            '--passWithNoTests'
        )
    } finally {
        Pop-Location
    }
    Add-Step '9/9 ui-tui vitest (optional)' -Ok $vitestOk -Detail 'statusBarThroughput + usageCostBar'
} else {
    Write-Host '[SKIP] 9/9 ui-tui vitest — npm of ui-tui ontbreekt' -ForegroundColor Yellow
}

$reportPath = Join-Path $scriptRoot ("NOUS_OVERLAY_INSTITUTIONAL_E2E_REPORT_" + $reportStamp + '.md')
$status = if ($failures -eq 0) { 'PASS' } else { "FAIL ($failures)" }
@"
# Nous Overlay Institutional E2E — $status

Generated: $reportStamp
Repo: $RepoRoot
Python: $python

## Scope

- Tier A byte-identiek met upstream (strict drift gate)
- Overlay bootstrap + CLI/pricing/catalog patches
- Status bar cost + gemini pricing + verify/smoke scripts

"@ | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host ''
Write-Host "=== NOUS OVERLAY INSTITUTIONAL E2E: $status ===" -ForegroundColor $(if ($failures -eq 0) { 'Green' } else { 'Red' })
Write-Host "Report: $reportPath"

if ($failures -gt 0) { exit 1 }
exit 0
