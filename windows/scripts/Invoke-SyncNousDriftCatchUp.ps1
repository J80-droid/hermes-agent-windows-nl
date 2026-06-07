# Automated tier-A drift catch-up after upstream/main moves. SSOT: docs/NOUS_DRIFT_MAINTENANCE.md
param(
    [string]$RepoRoot = '',
    [string]$UpstreamRef = 'upstream/main',
    [int]$TargetedMaxPaths = 15,
    [switch]$SkipForkGate,
    [switch]$SkipBaseline,
    [switch]$Commit,
    [string]$CommitMessage = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'HermesNousDrift.ps1')

$repo = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { Get-HermesRepoRootFromNousScripts -Start $PSScriptRoot }
$windowsDir = Join-Path $repo 'windows'

Write-Host '=== Nous drift catch-up ===' -ForegroundColor Cyan
Write-Host "Repo: $repo" -ForegroundColor DarkGray
Write-Host "Policy: docs/NOUS_DRIFT_MAINTENANCE.md" -ForegroundColor DarkGray

$report = Get-HermesNousTierADriftReport -RepoRoot $repo -UpstreamRef $UpstreamRef
foreach ($w in $report.ForkIntentional) {
    Write-Host "[WARN] fork-intentional (allowed): $w" -ForegroundColor Yellow
}

if ($report.MustUpstreamDrift.Count -eq 0) {
    Write-Host '[OK] Drift 0 - geen sync nodig.' -ForegroundColor Green
} else {
    Write-Host ("[INFO] {0} tier-A pad(en) wijken af - sync starten" -f $report.MustUpstreamDrift.Count) -ForegroundColor Yellow
    if ($report.MustUpstreamDrift.Count -le $TargetedMaxPaths) {
        Invoke-HermesNousTierATargetedCheckout -RepoRoot $repo -Paths $report.MustUpstreamDrift -UpstreamRef $UpstreamRef
    } else {
        $restore = Join-Path $PSScriptRoot 'Invoke-RestoreNousTierA.ps1'
        & $restore -RepoRoot $repo -UpstreamRef $UpstreamRef
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    $recheck = Get-HermesNousTierADriftReport -RepoRoot $repo -UpstreamRef $UpstreamRef -SkipFetch
    if ($recheck.MustUpstreamDrift.Count -gt 0) {
        Write-Host "[FAIL] Drift na sync: $($recheck.MustUpstreamDrift.Count) pad(en)" -ForegroundColor Red
        foreach ($p in $recheck.MustUpstreamDrift) { Write-Host "  $p" -ForegroundColor Red }
        exit 1
    }
    Write-Host '[OK] Drift 0 na sync.' -ForegroundColor Green
}

if (-not $SkipForkGate) {
    Write-Host '=== pytest fork gate ===' -ForegroundColor Cyan
    $forkGate = Join-Path $repo 'windows/tests/RUN_PYTEST_FORK_GATE.bat'
    cmd /c "`"$forkGate`""
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] fork gate (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host '[OK] fork gate' -ForegroundColor Green
}

if (-not $SkipBaseline) {
    $export = Join-Path $PSScriptRoot 'Export-NousDriftBaseline.ps1'
    & $export -RepoRoot $repo -UpstreamRef $UpstreamRef
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Commit) {
    $status = @(git -C $repo status --porcelain 2>$null | Where-Object { $_.Trim() })
    if ($status.Count -eq 0) {
        Write-Host '[OK] Geen wijzigingen om te committen.' -ForegroundColor Green
        exit 0
    }
    git -C $repo add -A
    $msg = if ($CommitMessage) { $CommitMessage } else { 'chore(nous): sync tier-A to upstream/main (drift catch-up)' }
    git -C $repo commit -m $msg
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "[OK] Commit: $msg" -ForegroundColor Green
}

Write-Host '=== Drift catch-up geslaagd ===' -ForegroundColor Green
exit 0
