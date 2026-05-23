# Legacy entry: sync Values + Trust & verification (replaces ## Advisory & trust).
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$scriptDir = $PSScriptRoot

Write-Host '--- SOUL Advisory (legacy) -> Values + Trust ---' -ForegroundColor Cyan
& (Join-Path $scriptDir 'sync_soul_values_snippet.ps1') -RepoRoot $RepoRoot -HermesRoot $HermesRoot -Force:$Force
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& (Join-Path $scriptDir 'sync_soul_trust_verification_snippet.ps1') -RepoRoot $RepoRoot -HermesRoot $HermesRoot -Force:$Force
exit $LASTEXITCODE
