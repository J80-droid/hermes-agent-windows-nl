# Kopieer repo fixtures/rag_minimal naar %USERPROFILE%\data\raw_source_files\ (idempotent).
param(
    [string]$RepoRoot = '',
    [string]$DestRoot = '',
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

if (-not $DestRoot) {
    $DestRoot = Join-Path $env:USERPROFILE 'data\raw_source_files'
}

$srcRoot = Join-Path $RepoRoot 'fixtures\rag_minimal'
if (-not (Test-Path -LiteralPath $srcRoot)) {
    Write-HermesErr "fixtures/rag_minimal ontbreekt: $srcRoot"
    exit 1
}

$count = 0
Get-ChildItem -LiteralPath $srcRoot -Directory | ForEach-Object {
    $dest = Join-Path $DestRoot $_.Name
    if ($WhatIf) {
        Write-HermesInfo "Would copy: $($_.FullName) -> $dest"
        return
    }
    if (-not (Test-Path -LiteralPath $dest)) {
        New-Item -ItemType Directory -Path $dest -Force | Out-Null
    }
    Copy-Item -Path (Join-Path $_.FullName '*') -Destination $dest -Recurse -Force
    $count++
}

if ($WhatIf) {
    Write-HermesInfo 'WhatIf: geen bestanden gekopieerd.'
    exit 0
}

Write-HermesOk "Seeded $count domein-map(pen) naar $DestRoot"
exit 0
