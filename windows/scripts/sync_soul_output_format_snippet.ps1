# Sync ## Outputformaat (institutioneel) from repo template into all profile SOUL.md files.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$Force,
    [switch]$Verify,
    [string]$ManifestPath = ''
)

$ErrorActionPreference = 'Stop'

$modulePath = Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1'
if (-not (Test-Path -LiteralPath $modulePath)) {
    throw "SyncSoulSnippet module ontbreekt: $modulePath"
}
Import-Module "$modulePath" -Force

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$templatePath = Join-Path $RepoRoot 'docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md'

Write-Host '--- SOUL Outputformaat sync ---' -ForegroundColor Cyan
Sync-SoulSnippet `
    -TemplatePath $templatePath `
    -SectionRegex '^## Outputformaat \(institutioneel\)\s' `
    -InsertBeforeRegex '## Interaction met J\.\s' `
    -HermesRoot $HermesRoot `
    -Force:$Force `
    -Verify:$Verify `
    -ManifestPath $ManifestPath
