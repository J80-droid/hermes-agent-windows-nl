# Sync ## Workflow from repo template into all profile SOUL.md files.
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

$templatePath = Join-Path $RepoRoot 'docs/templates/SOUL_SHARED_WORKFLOW.md'

Write-Host '--- SOUL Workflow sync ---' -ForegroundColor Cyan
Sync-SoulSnippet `
    -TemplatePath $templatePath `
    -SectionRegex '^## Workflow\s' `
    -InsertBeforeRegex '## Tool Usage\s|## Tool governance \(domein-minimum\)\s' `
    -HermesRoot $HermesRoot `
    -Force:$Force `
    -Verify:$Verify `
    -ManifestPath $ManifestPath
