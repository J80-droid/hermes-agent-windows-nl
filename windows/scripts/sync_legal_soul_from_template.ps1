# Kopieer SOUL_LEGAL_DOMAIN template naar runtime legal/SOUL.md
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = ''
)

$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'sync_domain_soul_from_template.ps1') -Profile legal -RepoRoot $RepoRoot -HermesRoot $HermesRoot
exit $LASTEXITCODE
