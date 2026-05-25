# Eenmalig/herstel: MCP + multi-profile secties in core MEMORY (na misplaatsing in legal/root).
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

. (Join-Path $PSScriptRoot 'HermesMemoryMergeCommon.ps1')

$root = Get-HermesMemoryHermesRoot -OverrideRoot $HermesRoot
$coreMemPath = Join-HermesRepoPath -RepoRoot $root -RelativePath 'profiles/core/memories/MEMORY.md'
if (-not (Test-Path -LiteralPath $coreMemPath)) {
    Write-Host '[SKIP] core MEMORY ontbreekt' -ForegroundColor Yellow
    exit 0
}

$raw = Get-Content -LiteralPath $coreMemPath -Raw -Encoding UTF8
if (Test-MemoryHermesConfigSection -Text $raw) {
    Write-Host '[SKIP] core bevat al Hermes-config secties' -ForegroundColor DarkGray
    exit 0
}

$restore = @(
    "De MCP-server 'lancedb-knowledge' is geconfigureerd in C:\Users\J.\AppData\Local\hermes\config.yaml met de Python-interpreter uit de Miniconda 'hermes-env'. De 'args' moeten als een YAML-lijst worden opgegeven, niet als een JSON-string. Dit is essentieel voor een succesvolle verbinding via de stdio-transportlaag.",
    'Hermes multi-profile configuration rules: 1. Store API keys ONLY in the global environment variables file (profiles inherit them automatically; do not duplicate into profile folders). 2. Register MCP servers per-profile (in their specific config.yaml), NOT globally, to ensure strict Kanban worker isolation.'
)

$memorySeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'MEMORY.md'
Merge-MemoryFile -FilePath $coreMemPath -SeedEntries $memorySeed -ExtraExisting $restore -DryRun:$DryRun
Write-Host '[OK] Hermes-config hersteld in core' -ForegroundColor Cyan
