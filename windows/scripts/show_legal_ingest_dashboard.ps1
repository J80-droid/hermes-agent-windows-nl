#requires -Version 5.1
<#
.SYNOPSIS
  Toon legal LanceDB ingest-status (summary, state, live).
#>
param(
    [string]$DbPath = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

if (-not $DbPath) {
    $DbPath = Join-Path $env:USERPROFILE 'data\lancedb\legal'
}

Write-Host ''
Write-Host 'Legal ingest dashboard' -ForegroundColor Cyan
Write-Host "  LanceDB: $DbPath"
Write-Host ''

foreach ($name in @(
    'rag_ingest_run_summary.json',
    '.hermes_rag_ingest_state.json',
    'rag_ingest_live_status.json',
    'rag_ingest_skipped_report.json'
)) {
    $p = Join-Path $DbPath $name
    if (Test-Path -LiteralPath $p) {
        Write-Host "[OK] $name" -ForegroundColor Green
        if ($name -eq 'rag_ingest_run_summary.json') {
            try {
                $j = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
                if ($j.indexed) { Write-Host "     indexed: $($j.indexed)" }
                if ($j.scanned) { Write-Host "     scanned: $($j.scanned)" }
            } catch { $null = $_ }
        }
    } else {
        Write-Host "[--] $name (ontbreekt)" -ForegroundColor DarkGray
    }
}

$readiness = Join-Path $PSScriptRoot 'Get-RagSourceReadiness.ps1'
if (Test-Path -LiteralPath $readiness) {
    Write-Host ''
    & $readiness
}
Write-Host ''
exit 0
