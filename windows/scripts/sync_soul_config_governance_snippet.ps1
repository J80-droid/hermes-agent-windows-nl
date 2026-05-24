# Sync ## Config governance (Windows) from repo template into all profile SOUL.md files.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$Force,
    [switch]$Verify,
    [string]$ManifestPath = ''
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$templatePath = Join-Path $RepoRoot 'docs/templates/SOUL_SHARED_CONFIG_GOVERNANCE.md'

Write-Host '--- SOUL Config governance (Windows) sync ---' -ForegroundColor Cyan
$null = Sync-SoulSnippet `
    -TemplatePath $templatePath `
    -SectionRegex '^## Config governance \(Windows\)\s' `
    -InsertBeforeRegex '^## Communication Style\s|^## Identity\s' `
    -HermesRoot $HermesRoot `
    -Force:$Force `
    -Verify:$Verify `
    -ManifestPath $ManifestPath
exit 0
