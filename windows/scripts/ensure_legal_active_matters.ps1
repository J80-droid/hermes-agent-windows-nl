#requires -Version 5.1
<#
.SYNOPSIS
  Seed profiles/legal/LEGAL_ACTIVE_MATTERS.md from repo example (never overwrite).
#>
param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

if (-not $RepoRoot) {
    if ($env:HERMES_REPO_ROOT) { $RepoRoot = $env:HERMES_REPO_ROOT.Trim().Trim('"') }
    else { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$hermesRoot = Join-Path $env:LOCALAPPDATA 'hermes'
if (-not (Test-Path -LiteralPath (Join-Path $hermesRoot 'config.yaml'))) {
    $alt = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $alt 'config.yaml')) { $hermesRoot = $alt }
}

$destDir = Join-Path $hermesRoot 'profiles\legal'
$dest = Join-Path $destDir 'LEGAL_ACTIVE_MATTERS.md'
$example = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/templates/LEGAL_ACTIVE_MATTERS.example.md'

if (-not (Test-Path -LiteralPath $example)) {
    Write-HermesWarn "Example ontbreekt: $example"
    exit 1
}

if (-not (Test-Path -LiteralPath $destDir)) {
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
}

if (Test-Path -LiteralPath $dest) {
    if (-not $Quiet) { Write-HermesLaunchUi -Message "LEGAL_ACTIVE_MATTERS bestaat al (niet overschreven)." -Level Detail }
    exit 0
}

Copy-Item -LiteralPath $example -Destination $dest -Force
if (-not $Quiet) { Write-HermesLaunchUi -Message "LEGAL_ACTIVE_MATTERS aangemaakt vanuit template." -Level Ok }
exit 0
