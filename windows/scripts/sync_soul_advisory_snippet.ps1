# Legacy entry: sync Values + Trust & verification (replaces ## Advisory & trust).
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force
$scriptDir = $PSScriptRoot

Write-Host '--- SOUL Advisory (legacy) -> Values + Trust ---' -ForegroundColor Cyan
& (Join-Path $scriptDir 'sync_soul_values_snippet.ps1') -RepoRoot $RepoRoot -HermesRoot $HermesRoot -Force:$Force
if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
& (Join-Path $scriptDir 'sync_soul_trust_verification_snippet.ps1') -RepoRoot $RepoRoot -HermesRoot $HermesRoot -Force:$Force
if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
exit 0
