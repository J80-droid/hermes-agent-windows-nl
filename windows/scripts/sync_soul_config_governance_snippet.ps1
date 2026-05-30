# Sync ## Config governance (Windows) from repo template into all profile SOUL.md files.
# InsertBeforeRegex: alleen vóór ## Identity (niet vóór Communication Style — voorkomt dubbele blokken).
# Dubbele koppen: Repair-SoulDuplicateConfigGovernanceBlocks in sync_soul_anatomy_snippets.ps1.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$Force,
    [switch]$Verify,
    [string]$ManifestPath = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$templatePath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/templates/SOUL_SHARED_CONFIG_GOVERNANCE.md'

Write-Host '--- SOUL Config governance (Windows) sync ---' -ForegroundColor Cyan
$null = Sync-SoulSnippet `
    -TemplatePath $templatePath `
    -SectionRegex '^## Config governance \(Windows\)\s' `
    -InsertBeforeRegex '^## Identity\s' `
    -HermesRoot $HermesRoot `
    -Force:$Force `
    -Verify:$Verify `
    -ManifestPath $ManifestPath
exit 0
