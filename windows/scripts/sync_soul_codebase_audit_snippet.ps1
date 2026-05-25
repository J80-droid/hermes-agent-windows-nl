# Sync ### Codebase-audit (smoke vs release) from repo template into all profile SOUL.md files.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$Force,
    [switch]$Verify,
    [string]$ManifestPath = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

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

$templatePath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/templates/SOUL_SHARED_CODEBASE_AUDIT.md'

Write-Host '--- SOUL Codebase-audit sync ---' -ForegroundColor Cyan
$null = Sync-SoulSnippet `
    -TemplatePath $templatePath `
    -SectionRegex '^### Codebase-audit \(smoke vs release\)\s' `
    -InsertBeforeRegex '## Expertise & Knowledge\s' `
    -HermesRoot $HermesRoot `
    -Force:$Force `
    -Verify:$Verify `
    -ManifestPath $ManifestPath

if ($Force -and -not $Verify) {
    Set-InstitutionalNewChatReminder -Reason 'SOUL Codebase-audit sync'
}
exit 0
