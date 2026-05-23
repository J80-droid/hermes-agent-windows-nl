# Sync ## Tool Usage from repo template into all profile SOUL.md files.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$Force,
    [switch]$Verify
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$templatePath = Join-Path $RepoRoot 'docs/templates/SOUL_SHARED_TOOL_GOVERNANCE.md'

Write-Host '--- SOUL Tool Usage sync ---' -ForegroundColor Cyan
$null = Sync-SoulSnippet `
    -TemplatePath $templatePath `
    -SectionRegex '^## Tool Usage\s' `
    -LegacySectionRegex @('^## Tool governance \(domein-minimum\)\s') `
    -InsertBeforeRegex '## Memory Policy\s|## Example Interaction\s|## Workflow\s' `
    -HermesRoot $HermesRoot `
    -Force:$Force `
    -Verify:$Verify
exit 0
