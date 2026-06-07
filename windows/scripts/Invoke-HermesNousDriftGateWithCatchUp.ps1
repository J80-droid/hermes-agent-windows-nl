# Tier-A drift gate with automatic catch-up. SSOT: docs/NOUS_DRIFT_MAINTENANCE.md
param(
    [string]$RepoRoot = '',
    [string]$UpstreamRef = 'upstream/main',
    [switch]$AllowTransitional,
    [switch]$SkipCatchUp,
    [switch]$Commit,
    [string]$CommitMessage = '',
    [switch]$Strict,
    [int]$TargetedMaxPaths = 15,
    [switch]$SkipForkGate,
    [switch]$SkipBaseline
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'HermesNousDrift.ps1')

$repo = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { Get-HermesRepoRootFromNousScripts -Start $PSScriptRoot }

$rc = Invoke-HermesNousDriftGateWithCatchUp `
    -RepoRoot $repo `
    -UpstreamRef $UpstreamRef `
    -AllowTransitional:$AllowTransitional `
    -SkipCatchUp:$SkipCatchUp `
    -Commit:$Commit `
    -CommitMessage $CommitMessage `
    -Strict:$Strict `
    -TargetedMaxPaths $TargetedMaxPaths `
    -SkipForkGate:$SkipForkGate `
    -SkipBaseline:$SkipBaseline

exit $rc
