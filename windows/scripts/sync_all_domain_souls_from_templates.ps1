# Push alle repo SOUL domein-templates naar runtime + anatomy snippet sync.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$SkipSnippetSync,
    [switch]$UpdateDeployStamp
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

$profiles = Get-DomainSoulProfileNames
$total = @($profiles).Count
if ($total -lt 1) { $total = 1 }

Write-HermesLaunchUi -Message 'Push domain SOUL templates' -Level Info
$failedProfiles = [System.Collections.Generic.List[string]]::new()
$idx = 0
foreach ($p in $profiles) {
    $idx++
    Update-HermesLaunchActivity -Reason ('template ' + $idx + '/' + $total + ' (' + $p + ')') -ProgressCurrent $idx -ProgressTotal $total
    & (Join-Path $PSScriptRoot 'sync_domain_soul_from_template.ps1') -ProfileName $p -RepoRoot $RepoRoot -HermesRoot $HermesRoot -SuppressTip
    if (Test-NativeCommandFailed) {
        [void]$failedProfiles.Add($p)
        Write-HermesLaunchUi -Message ('Overgeslagen of mislukt: ' + $p) -Level Warn
    }
}
if ($failedProfiles.Count -gt 0) {
    Write-HermesLaunchUi -Message ('Domein-template sync mislukt voor: ' + ($failedProfiles -join ', ')) -Level Error -ForceConsole
    exit 1
}

$ensureMatters = Join-Path $PSScriptRoot 'ensure_legal_active_matters.ps1'
if (Test-Path -LiteralPath $ensureMatters) {
    & $ensureMatters -RepoRoot $RepoRoot -Quiet
}

$legalLens = Join-Path $PSScriptRoot 'sync_legal_lens_from_taxonomy.ps1'
if (Test-Path -LiteralPath $legalLens) {
    Write-HermesLaunchUi -Message 'Legal lenzentabel (LEGAL_TAXONOMY)' -Level Info
    & $legalLens -RepoRoot $RepoRoot -Quiet
    if (Test-NativeCommandFailed) {
        Write-HermesLaunchUi -Message ('Legal lens sync mislukt (exit ' + $LASTEXITCODE + ')') -Level Error -ForceConsole
        exit 1
    }
}

if ($SkipSnippetSync) {
    Write-HermesLaunchUi -Message 'Snippet sync overgeslagen' -Level Warn
    exit 0
}

Write-HermesLaunchUi -Message 'SOUL anatomy snippet sync (Force)' -Level Info
& (Join-Path $PSScriptRoot 'sync_soul_anatomy_snippets.ps1') -RepoRoot $RepoRoot -HermesRoot $HermesRoot -Force -Quiet
if (Test-NativeCommandFailed) {
    Write-HermesLaunchUi -Message ('SOUL anatomy snippet sync mislukt (exit ' + $LASTEXITCODE + ')') -Level Error -ForceConsole
    exit 1
}

Write-HermesLaunchUi -Message 'Root SOUL fallback (legacy)' -Level Info
& (Join-Path $PSScriptRoot 'sync_root_soul_fallback.ps1') -RepoRoot $RepoRoot -HermesRoot $HermesRoot -Quiet
if (Test-NativeCommandFailed) {
    Write-HermesLaunchUi -Message ('Root SOUL fallback sync mislukt (exit ' + $LASTEXITCODE + ')') -Level Error -ForceConsole
    exit 1
}

if ($UpdateDeployStamp) {
    Set-SoulAnatomyDeployStamp
}
Write-HermesLaunchUi -Message 'Alle domein-SOUL templates + snippets toegepast. Start /new in Hermes.' -Level Ok
exit 0
