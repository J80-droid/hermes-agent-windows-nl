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

$domainDirs = @(Get-ChildItem -LiteralPath $srcRoot -Directory)
if ($domainDirs.Count -eq 0) {
    Write-HermesErr "geen domein-mappen onder fixtures/rag_minimal: $srcRoot"
    exit 1
}

$count = 0
foreach ($dir in $domainDirs) {
    $dest = Join-Path $DestRoot $dir.Name
    if ($WhatIf) {
        Write-HermesInfo "Would copy: $($dir.FullName) -> $dest"
        continue
    }
    if (-not (Test-Path -LiteralPath $dest)) {
        New-Item -ItemType Directory -Path $dest -Force | Out-Null
    }
    $files = @(Get-ChildItem -LiteralPath $dir.FullName -File)
    if ($files.Count -eq 0) {
        Write-HermesWarn "overslaan lege fixture-map: $($dir.Name)"
        continue
    }
    Copy-Item -Path (Join-Path $dir.FullName '*') -Destination $dest -Recurse -Force
    $count++
}

if ($WhatIf) {
    Write-HermesInfo 'WhatIf: geen bestanden gekopieerd.'
    exit 0
}

if ($count -eq 0) {
    Write-HermesErr 'geen fixture-bestanden gekopieerd (alle mappen leeg?)'
    exit 1
}

Write-HermesOk "Seeded $count domein-map(pen) naar $DestRoot"
exit 0
