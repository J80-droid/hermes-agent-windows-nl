# Orchestrator: legacy migratie (-MigrateOnly) en/of dedup+enforce+layout (-EnforceOnly / -Full).
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$MigrateOnly,
    [switch]$EnforceOnly,
    [switch]$Full,
    [switch]$DryRun,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'HermesMemoryMergeCommon.ps1')
. (Join-Path $PSScriptRoot 'MemoryAuditCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$root = Get-HermesMemoryHermesRoot -OverrideRoot $HermesRoot
if ($MigrateOnly.IsPresent -and $EnforceOnly.IsPresent) {
    Write-Host '[FAIL] Gebruik -MigrateOnly, -EnforceOnly of -Full (niet combineerbaar).' -ForegroundColor Red
    exit 1
}
$runMigrate = $MigrateOnly.IsPresent -or $Full.IsPresent
$runEnforce = $EnforceOnly.IsPresent -or $Full.IsPresent
if (-not $runMigrate -and -not $runEnforce) {
    $runMigrate = $true
    $runEnforce = $true
}

function Write-RepairStep([string]$Msg) {
    if (-not $Quiet) { Write-Host "[INFO] $Msg" -ForegroundColor Cyan }
}

if ($runMigrate) {
    $legacyMem = Join-Path $root (Join-Path 'memories' 'MEMORY.md')
    if (Test-Path -LiteralPath $legacyMem) {
        Write-RepairStep 'Legacy root MEMORY — consolidate migratie'
        $consolidate = Join-Path $PSScriptRoot 'consolidate_root_hermes_memories.ps1'
        if ($DryRun) {
            & $consolidate -RepoRoot $RepoRoot -HermesRoot $root -DryRun
        } else {
            & $consolidate -RepoRoot $RepoRoot -HermesRoot $root
        }
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } elseif (-not $Quiet) {
        Write-Host '[SKIP] Geen legacy root memories/MEMORY.md' -ForegroundColor DarkGray
    }
}

if ($runEnforce) {
    Ensure-HermesLegacyRootMemorySeed -HermesRoot $root -RepoRoot $RepoRoot -DryRun:$DryRun

    $dedup = Join-Path $PSScriptRoot 'invoke_deduplicate_memories.ps1'
    if (Test-Path -LiteralPath $dedup) {
        Write-RepairStep 'deduplicate_memories'
        if ($DryRun) {
            Write-RepairStep 'deduplicate_memories (DryRun — overgeslagen)'
        } else {
            & $dedup -RepoRoot $RepoRoot -HermesRoot $root
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
    }

    $enforce = Join-Path $PSScriptRoot 'enforce_profile_memory_char_limits.ps1'
    Write-RepairStep 'enforce_profile_memory_char_limits'
    $enforceArgs = @{ RepoRoot = $RepoRoot; HermesRoot = $root; Quiet = $Quiet }
    if ($DryRun) { $enforceArgs['DryRun'] = $true }
    & $enforce @enforceArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $layoutFails = Test-MemoryConsolidationLayout -HermesRoot $root
    $needsRestore = @($layoutFails | Where-Object { $_ -match 'core: Hermes-config ontbreekt' })
    if ($needsRestore.Count -gt 0) {
        $restore = Join-Path $PSScriptRoot 'restore_core_hermes_config_memory.ps1'
        if (Test-Path -LiteralPath $restore) {
            Write-RepairStep 'restore_core_hermes_config_memory (layout)'
            if (-not $DryRun) {
                & $restore -RepoRoot $RepoRoot -HermesRoot $root
                & $enforce @enforceArgs
                if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            }
        }
    }
}

if (-not $Quiet) {
    Write-Host '[OK] Invoke-RepairProfileMemoryLimits voltooid.' -ForegroundColor Green
}
exit 0
