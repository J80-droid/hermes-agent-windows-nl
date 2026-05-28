#requires -Version 5.1
<#
.SYNOPSIS
  Rapport: bronbestanden per domeinmap + laatste legal ingest-summary.

.EXIT
  0 = bronnen aanwezig (minstens 1 bestand)
  2 = alle domeinen leeg (geen ingest starten)
  1 = fout
#>
param(
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$winDir = Split-Path -Parent $scriptDir

. (Join-Path $winDir 'HermesShellCommon.ps1')

if ($RepoRoot) {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$rawRoot = Join-Path $env:USERPROFILE 'data\raw_source_files'
if (-not (Test-Path -LiteralPath $rawRoot)) {
    Write-HermesWarn "Map ontbreekt: $rawRoot"
    exit 2
}

$totalFiles = 0
$rows = @()
Get-ChildItem -LiteralPath $rawRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $count = @(Get-ChildItem -LiteralPath $_.FullName -Recurse -File -ErrorAction SilentlyContinue).Count
    $totalFiles += $count
    $rows += [pscustomobject]@{ Domain = $_.Name; Files = $count }
}

Write-Host ''
Write-Host 'RAG bron-readiness' -ForegroundColor Cyan
Write-Host "  raw_source_files: $rawRoot"
Write-Host ''
if ($rows.Count -gt 0) {
    $rows | Sort-Object Domain | Format-Table -AutoSize | Out-String | ForEach-Object { Write-Host $_ }
}

$summaryPath = Join-Path $env:USERPROFILE 'data\lancedb\legal\rag_ingest_run_summary.json'
if (Test-Path -LiteralPath $summaryPath) {
    Write-Host "Laatste legal ingest summary: $summaryPath" -ForegroundColor DarkGray
}

if ($totalFiles -le 0) {
    Write-HermesWarn 'Geen bronbestanden gevonden — plaats bestanden in raw_source_files-mappen.'
    exit 2
}

Write-HermesOk ("Totaal $totalFiles bronbestand(en) gevonden.")
exit 0
