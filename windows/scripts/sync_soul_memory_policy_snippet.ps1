# Sync ## Memory Policy from repo template into all profile SOUL.md files.
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

$templatePath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/templates/SOUL_SHARED_MEMORY_POLICY.md'

Write-Host '--- SOUL Memory Policy sync ---' -ForegroundColor Cyan
$null = Sync-SoulSnippet `
    -TemplatePath $templatePath `
    -SectionRegex '^## Memory Policy\s' `
    -InsertBeforeRegex '## Example Interaction\s' `
    -HermesRoot $HermesRoot `
    -Force:$Force `
    -Verify:$Verify `
    -ManifestPath $ManifestPath
exit 0
