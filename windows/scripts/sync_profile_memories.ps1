# Merge canonical Trust & Forensic memory seed into root + all profile memories/.
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
$userSeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'USER.md'
$memorySeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'MEMORY.md'
Initialize-PendingHermesConfigSections

$targets = @(
    @{ User = Join-HermesRepoPath -RepoRoot $root -RelativePath 'memories/USER.md'; Memory = Join-HermesRepoPath -RepoRoot $root -RelativePath 'memories/MEMORY.md' }
)
$profilesDir = Join-Path $root 'profiles'
if (Test-Path -LiteralPath $profilesDir) {
    Get-ChildItem -LiteralPath $profilesDir -Directory | ForEach-Object {
        $targets += @{
            User   = Join-Path $_.FullName 'memories/USER.md'
            Memory = Join-Path $_.FullName 'memories/MEMORY.md'
        }
    }
}

foreach ($t in $targets) {
    Merge-MemoryFile -FilePath $t.User -SeedEntries $userSeed -DryRun:$DryRun
    Merge-MemoryFile -FilePath $t.Memory -SeedEntries $memorySeed -DryRun:$DryRun
}

if (-not $DryRun) {
    Invoke-RebalanceHermesConfigToCore -HermesRoot $root -RepoRoot $RepoRoot
    Export-PendingHermesConfigToCore -HermesRoot $root -RepoRoot $RepoRoot -DryRun:$DryRun
    $restorePs1 = Join-Path $PSScriptRoot 'restore_core_hermes_config_memory.ps1'
    if (Test-Path -LiteralPath $restorePs1) {
        & $restorePs1 -RepoRoot $RepoRoot -HermesRoot $root
    }
}

if (-not $DryRun) {
    $dedupPs1 = Join-Path $PSScriptRoot 'invoke_deduplicate_memories.ps1'
    if (Test-Path -LiteralPath $dedupPs1) {
        Write-Host '[INFO] Post-merge §-dedup...' -ForegroundColor Gray
        & $dedupPs1 -RepoRoot $RepoRoot
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

Write-Host '[INFO] Memory seed merge voltooid (profiel-scoped leidend bij actief profiel).' -ForegroundColor Cyan
