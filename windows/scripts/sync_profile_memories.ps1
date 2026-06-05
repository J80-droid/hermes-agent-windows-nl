# Merge canonical Trust & Forensic memory seed into root + all profile memories/.
# Legal-only: sectie "legal USER.md" in MEMORY_CANONICAL_SEED.md → SeedEntries voor profiles/legal/memories/USER.md.
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
$legalUserSeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'legal USER.md' -Optional
if ($legalUserSeed.Count -eq 0) {
    Write-Host '[WARN] legal USER.md seed-sectie ontbreekt of is leeg in MEMORY_CANONICAL_SEED.md' -ForegroundColor Yellow
}
Initialize-HermesLegacyRootMemorySeed -HermesRoot $root -RepoRoot $RepoRoot -DryRun:$DryRun
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
    $userEntries = @($userSeed)
    if ($legalUserSeed.Count -gt 0 -and (Test-IsLegalProfileMemoryUserPath -FilePath $t.User)) {
        $userEntries = @($userSeed) + @($legalUserSeed)
        # Vervang verouderde legal-domain USER-secties vóór canonical seed-merge.
        if (-not $DryRun -and (Test-Path -LiteralPath $t.User)) {
            $raw = Get-Content -LiteralPath $t.User -Raw -Encoding UTF8
            $sections = Split-MemoryMarkdownSections -Raw $raw
            $kept = @($sections | Where-Object { -not (Test-MemoryLegalDomainSection -Text $_) })
            if ($kept.Count -lt $sections.Count) {
                $delim = Get-MemorySectionDelimiterChar
                $out = if ($kept.Count -gt 0) { ($kept -join "`n$delim`n") + "`n" } else { '' }
                Set-Content -LiteralPath $t.User -Value $out -Encoding UTF8 -NoNewline
                Write-Host "[OK] stale legal-domain USER sections verwijderd: $($t.User)" -ForegroundColor Green
            }
        }
    }
    Merge-MemoryFile -FilePath $t.User -SeedEntries $userEntries -DryRun:$DryRun
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
        & $dedupPs1 -RepoRoot $RepoRoot -HermesRoot $root
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

Write-Host '[INFO] Memory seed merge voltooid (profiel-scoped leidend bij actief profiel).' -ForegroundColor Cyan
