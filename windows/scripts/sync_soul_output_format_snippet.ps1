# Sync ### Output conventions (institutional) from repo template into all profile SOUL.md files.
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

$templatePath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md'

Write-Host '--- SOUL Output conventions sync ---' -ForegroundColor Cyan
$null = Sync-SoulSnippet `
    -TemplatePath $templatePath `
    -SectionRegex '^### Output conventions \(institutional\)\s' `
    -LegacySectionRegex @('^## Outputformaat \(institutioneel\)\s') `
    -InsertBeforeRegex '## Expertise & Knowledge\s' `
    -HermesRoot $HermesRoot `
    -Force:$Force `
    -Verify:$Verify `
    -ManifestPath $ManifestPath

if (-not $Verify) {
    foreach ($path in (Get-SoulTargets -HermesRoot $HermesRoot)) {
        $content = Get-SoulFileContent -Path $path
        $fixed = Repair-SoulDuplicateOutputBlocks -Content $content
        if ($fixed -ne $content) {
            Set-SoulFileContent -Path $path -Content $fixed
            Write-Host ('  REPAIR: ' + $path) -ForegroundColor Yellow
        }
    }
    if ($Force) {
        Set-InstitutionalNewChatReminder -Reason 'SOUL Output conventions sync'
    }
}
exit 0
