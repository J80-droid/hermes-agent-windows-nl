# Push alle repo SOUL domein-templates naar runtime + anatomy snippet sync.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$SkipSnippetSync
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

$profiles = Get-DomainSoulProfileNames

Write-Host '=== Push domain SOUL templates ===' -ForegroundColor Cyan
foreach ($p in $profiles) {
    & (Join-Path $PSScriptRoot 'sync_domain_soul_from_template.ps1') -ProfileName $p -RepoRoot $RepoRoot -HermesRoot $HermesRoot
    if (-not $?) {
        Write-Warning "Overgeslagen of mislukt: $p"
    }
}

if ($SkipSnippetSync) {
    Write-Host '[SKIP] Snippet sync' -ForegroundColor Yellow
    exit 0
}

Write-Host '=== SOUL anatomy snippet sync (Force) ===' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'sync_soul_anatomy_snippets.ps1') -RepoRoot $RepoRoot -HermesRoot $HermesRoot -Force -Quiet
if (-not $?) {
    Write-Error 'SOUL anatomy snippet sync mislukt'
    exit 1
}
Write-Host '[OK] Alle domein-SOUL templates + snippets toegepast. Start /new in Hermes.' -ForegroundColor Green
exit 0
