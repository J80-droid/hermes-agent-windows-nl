# Fail if Tier A paths differ from upstream/main (Nous 100% intact gate).
param(
    [string]$RepoRoot = '',
    [string]$UpstreamRef = 'upstream/main',
    [switch]$AllowTransitional,
    [switch]$SkipFetch,
    [switch]$Quiet
)

$script:NousDriftQuiet = [bool]$Quiet

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'HermesNousDrift.ps1')

function Write-DriftLine {
    param([string]$Msg, [string]$Level = 'Info')
    if ($script:NousDriftQuiet) { return }
    switch ($Level) {
        'Error' { Write-Host $Msg -ForegroundColor Red }
        'Warn' { Write-Host $Msg -ForegroundColor Yellow }
        default { Write-Host $Msg }
    }
}

$repo = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { Get-HermesRepoRootFromNousScripts -Start $PSScriptRoot }

$report = Get-HermesNousTierADriftReport -RepoRoot $repo -UpstreamRef $UpstreamRef -AllowTransitional:$AllowTransitional -SkipFetch:$SkipFetch

foreach ($w in $report.Warnings) {
    if (Test-HermesPathTierAForkIntentional -Path $w) {
        Write-DriftLine -Msg "[WARN] changed (fork-intentional): $w" -Level 'Warn'
    } elseif ($AllowTransitional) {
        Write-DriftLine -Msg "[WARN] changed (transitional): $w" -Level 'Warn'
    }
}

if ($report.Failures.Count -eq 0) {
    Write-DriftLine -Msg '[OK] Tier A identical to upstream (within policy).' -Level 'Info'
    exit 0
}

Write-DriftLine -Msg "[FAIL] Tier A drift: $($report.Failures.Count) issue(s)" -Level 'Error'
foreach ($f in $report.Failures) { Write-DriftLine -Msg "  changed: $f" -Level 'Error' }
Write-DriftLine -Msg 'Fix: windows\UPDATE_HERMES.bat (auto catch-up) — zie docs/NOUS_DRIFT_MAINTENANCE.md' -Level 'Warn'
exit 1
