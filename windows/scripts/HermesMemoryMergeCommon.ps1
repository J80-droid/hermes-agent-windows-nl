# Gedeelde §-merge helpers voor sync_profile_memories.ps1 en consolidate_root_hermes_memories.ps1

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
function Get-MemorySectionDelimiterChar {
    return [string][char]0x00A7
}

function Get-MemorySectionSplitPattern {
    $d = [regex]::Escape((Get-MemorySectionDelimiterChar))
    return "(?m)^$d\s*$"
}

function Get-HermesMemoryHermesRoot {
    param([string]$OverrideRoot = '')
    if ($OverrideRoot) {
        return (Resolve-Path -LiteralPath $OverrideRoot).Path
    }
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

function Get-HermesMemorySeedEntries {
    <#
    .SYNOPSIS
      Leest §-entries uit docs/templates/MEMORY_CANONICAL_SEED.md (één string per ```-blok).
    .PARAMETER SectionName
      Bijv. 'USER.md' (EN trust), 'legal USER.md' (3× NL triggers), 'MEMORY.md'.
    .NOTES
      Retourneert altijd een array — één entry anders unwrapped PowerShell-string (index op chars).
      E2E: audits/RUN_LEGAL_MEMORY_LANGUAGE_LAYERS_E2E.bat
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$SectionName,
        [switch]$Optional
    )
    $seedPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/templates/MEMORY_CANONICAL_SEED.md'
    if (-not (Test-Path -LiteralPath $seedPath)) {
        Write-Error "Seed ontbreekt: $seedPath"
    }
    $lines = Get-Content -LiteralPath $seedPath -Encoding UTF8
    $header = "## $SectionName entries"
    $inSection = $false
    $inFence = $false
    $entries = [System.Collections.Generic.List[string]]::new()
    foreach ($line in $lines) {
        if ($line.Trim() -eq $header) {
            $inSection = $true
            continue
        }
        if ($inSection -and $line -match '^## ') {
            if ($inFence) {
                Write-Warning ('MEMORY_CANONICAL_SEED: onafgesloten code fence in sectie ''' + $SectionName + ''' - entry mogelijk afgekapt.')
            }
            break
        }
        if (-not $inSection) { continue }
        if ($line.Trim() -eq '```') {
            $inFence = -not $inFence
            continue
        }
        if ($inFence) {
            $t = $line.Trim()
            if ($t) { [void]$entries.Add($t) }
        }
    }
    if ($entries.Count -eq 0) {
        if ($Optional) { return @() }
        Write-Error "Sectie niet gevonden of leeg in seed: $SectionName"
    }
    # Altijd array (voorkomt dat 1 entry als [char]-indexeerbare string wordt in callers).
    return @($entries.ToArray())
}

function Test-IsLegalProfileMemoryUserPath {
    param([Parameter(Mandatory)][string]$FilePath)
    $norm = ($FilePath -replace '\\', '/').ToLowerInvariant()
    return $norm -match '/profiles/legal/memories/user\.md$'
}

function Split-MemoryMarkdownSections {
    param([string]$Raw)
    if (-not $Raw.Trim()) { return @() }
    $lonelyC2 = [string][char]0x00C2
    $mojibakeLine = '(?m)^\s*' + [regex]::Escape($lonelyC2) + '\s*$'
    return @(
        $Raw -split (Get-MemorySectionSplitPattern) |
            ForEach-Object { ($_ -replace $mojibakeLine, '').Trim() } |
            Where-Object { $_ }
    )
}

function ConvertTo-MemorySectionNormalized {
    param([string]$Text)
    $lonelyC2 = [string][char]0x00C2
    $mojibakeLine = '(?m)^\s*' + [regex]::Escape($lonelyC2) + '\s*$'
    $cleaned = $Text -replace $mojibakeLine, ''
    $parts = $cleaned -split '\s+' | Where-Object { $_ }
    return ($parts -join ' ').ToLowerInvariant()
}

function Get-MemoryPolicyBucket {
    param([string]$Norm)
    if ([string]::IsNullOrWhiteSpace($Norm)) { return $null }
    if ($Norm.StartsWith('never compress')) { return 'yesman' }
    if ($Norm.StartsWith('rule for facts')) { return 'toolfail' }
    if ($Norm.StartsWith('trust protocol')) { return 'trust' }
    if ($Norm.StartsWith('j. demands absolute trust')) { return 'usertrust' }
    if ($Norm.StartsWith('user prefers option b') -or $Norm.StartsWith('user prefers the status bar cost')) {
        return 'statusbar'
    }
    return $null
}

function Test-MemoryRuntimeSection {
    param([string]$Text)
    return ($Text -match 'Hermes Windows Native quirks|canonical Python interpreter|OBSIDIAN_VAULT_PATH|Core profile: checkpoints')
}

function Test-MemoryUserPreferenceSection {
    param([string]$Text)
    return ($Text -match 'Monokai colors|asks about .kosten.|skins/|status-bar-dim|status-bar-strong|Exclusive Format')
}

function Test-MemoryLegalDomainSection {
    param([string]$Text)
    return ($Text -match 'Geschillencommissie|GCR 20|lancedb-legal|juridisch arbeidsgeschil|Rijksrecherche|hermetisch afschermen|knowledge_base|execute_code.*legal|Legal proactief|Legal triggers|Legal taallaag|voorbeeldvragen J\.|Parallelle invalshoeken|SOUL prevaleert')
}

function Test-MemoryHermesConfigSection {
    param([string]$Text)
    return ($Text -match 'multi-profile configuration|Register MCP servers per-profile|lancedb-knowledge')
}

function Test-IsCoreProfileMemoryPath {
    param([string]$FilePath)
    return ($FilePath -match '[\\/]profiles[\\/]core[\\/]memories[\\/]MEMORY\.md$')
}

function Initialize-PendingHermesConfigSections {
    $script:PendingHermesConfigSections = [System.Collections.Generic.List[string]]::new()
}

function Add-PendingHermesConfigSection {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return }
    $norm = ConvertTo-MemorySectionNormalized -Text $Text
    foreach ($existing in $script:PendingHermesConfigSections) {
        if ((ConvertTo-MemorySectionNormalized -Text $existing) -eq $norm) { return }
    }
    [void]$script:PendingHermesConfigSections.Add($Text)
}

function Export-PendingHermesConfigToCore {
    param(
        [Parameter(Mandatory)][string]$HermesRoot,
        [Parameter(Mandatory)][string]$RepoRoot,
        [switch]$DryRun
    )
    if (-not $script:PendingHermesConfigSections -or $script:PendingHermesConfigSections.Count -eq 0) { return }
    $coreMemPath = Join-HermesRepoPath -RepoRoot $HermesRoot -RelativePath 'profiles/core/memories/MEMORY.md'
    if (-not (Test-Path -LiteralPath (Split-Path -Parent $coreMemPath))) { return }
    $memorySeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'MEMORY.md'
    Write-HermesInfo ($script:PendingHermesConfigSections.Count.ToString() + ' Hermes-config sectie(s) naar core')
    if (-not $DryRun) {
        Merge-MemoryFile -FilePath $coreMemPath -SeedEntries $memorySeed -ExtraExisting $script:PendingHermesConfigSections.ToArray()
    }
    $script:PendingHermesConfigSections.Clear()
}

function Invoke-RebalanceHermesConfigToCore {
    param(
        [Parameter(Mandatory)][string]$HermesRoot,
        [Parameter(Mandatory)][string]$RepoRoot,
        [switch]$DryRun
    )
    $profilesDir = Join-Path $HermesRoot 'profiles'
    $coreMemPath = Join-HermesRepoPath -RepoRoot $HermesRoot -RelativePath 'profiles/core/memories/MEMORY.md'
    if (-not (Test-Path -LiteralPath $profilesDir)) { return }
    $memorySeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'MEMORY.md'
    $toCore = [System.Collections.Generic.List[string]]::new()

    Get-ChildItem -LiteralPath $profilesDir -Directory | Where-Object { $_.Name -ne 'core' } | ForEach-Object {
        $memPath = Join-Path $_.FullName 'memories/MEMORY.md'
        if (-not (Test-Path -LiteralPath $memPath)) { return }
        $sections = Split-MemoryMarkdownSections -Raw (Get-Content -LiteralPath $memPath -Raw -Encoding UTF8)
        $keep = [System.Collections.Generic.List[string]]::new()
        $profileToCore = [System.Collections.Generic.List[string]]::new()
        foreach ($sec in $sections) {
            if ((Test-MemoryHermesConfigSection -Text $sec) -and -not (Test-MemoryLegalDomainSection -Text $sec)) {
                [void]$profileToCore.Add($sec)
                [void]$toCore.Add($sec)
            } else {
                [void]$keep.Add($sec)
            }
        }
        if ($profileToCore.Count -eq 0) { return }
        Write-HermesInfo ($_.Name + ': ' + $profileToCore.Count.ToString() + ' Hermes-config sectie(s) -> core')
        if (-not $DryRun) {
            $delim = Get-MemorySectionDelimiterChar
            $out = ($keep -join "`n$delim`n") + "`n"
            Set-Content -LiteralPath $memPath -Value $out -Encoding UTF8 -NoNewline
        }
    }

    if ($toCore.Count -gt 0 -and (Test-Path -LiteralPath (Split-Path -Parent $coreMemPath))) {
        if ($DryRun) {
            Write-Host "[DRY] core +$($toCore.Count) Hermes-config sectie(s)" -ForegroundColor DarkGray
            return
        }
        Merge-MemoryFile -FilePath $coreMemPath -SeedEntries $memorySeed -ExtraExisting $toCore.ToArray()
    }
}

function Initialize-HermesLegacyRootMemorySeed {
    <#
    .SYNOPSIS
    Maakt ontbrekende legacy root memories/MEMORY.md en USER.md aan uit canonieke seed.
    Split-home: root blijft seed-only (~3 secties); profiel-scoped memory leidend.
    #>
    param(
        [Parameter(Mandatory)][string]$HermesRoot,
        [Parameter(Mandatory)][string]$RepoRoot,
        [switch]$DryRun
    )
    $userSeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'USER.md'
    $memorySeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'MEMORY.md'
    $pairs = @(
        @{ Path = Join-HermesRepoPath -RepoRoot $HermesRoot -RelativePath 'memories/USER.md'; Seed = $userSeed }
        @{ Path = Join-HermesRepoPath -RepoRoot $HermesRoot -RelativePath 'memories/MEMORY.md'; Seed = $memorySeed }
    )
    foreach ($pair in $pairs) {
        if (Test-Path -LiteralPath $pair.Path) { continue }
        Merge-MemoryFile -FilePath $pair.Path -SeedEntries $pair.Seed -DryRun:$DryRun
    }
}

function Merge-MemoryFile {
    param(
        [string]$FilePath,
        [string[]]$SeedEntries,
        [string[]]$ExtraExisting = @(),
        [switch]$DryRun
    )
    $existing = @()
    if (Test-Path -LiteralPath $FilePath) {
        $raw = Get-Content -LiteralPath $FilePath -Raw -Encoding UTF8
        $existing = Split-MemoryMarkdownSections -Raw $raw
    }
    if ($ExtraExisting.Count -gt 0) {
        $existing = @($existing) + @($ExtraExisting)
    }
    $merged = [System.Collections.Generic.List[string]]::new()
    $seenNorms = @{}
    $seenBuckets = @{}

    foreach ($e in $SeedEntries) {
        $norm = ConvertTo-MemorySectionNormalized -Text $e
        if (-not $norm -or $seenNorms.ContainsKey($norm)) { continue }
        $seenNorms[$norm] = $true
        $bucket = Get-MemoryPolicyBucket -Norm $norm
        if ($bucket) { $seenBuckets[$bucket] = $true }
        [void]$merged.Add($e)
    }
    foreach ($e in $existing) {
        $norm = ConvertTo-MemorySectionNormalized -Text $e
        if (-not $norm) { continue }
        if ($seenNorms.ContainsKey($norm)) { continue }
        if (Test-MemoryRuntimeSection -Text $e) {
            $seenNorms[$norm] = $true
            [void]$merged.Add($e)
            continue
        }
        if (Test-MemoryUserPreferenceSection -Text $e) {
            $seenNorms[$norm] = $true
            [void]$merged.Add($e)
            continue
        }
        if (Test-MemoryLegalDomainSection -Text $e) {
            $seenNorms[$norm] = $true
            [void]$merged.Add($e)
            continue
        }
        if (Test-MemoryHermesConfigSection -Text $e) {
            if (Test-IsCoreProfileMemoryPath -FilePath $FilePath) {
                $seenNorms[$norm] = $true
                [void]$merged.Add($e)
            } elseif ($null -ne $script:PendingHermesConfigSections) {
                Add-PendingHermesConfigSection -Text $e
            }
            continue
        }
        $bucket = Get-MemoryPolicyBucket -Norm $norm
        if ($bucket -and $seenBuckets.ContainsKey($bucket)) { continue }
        $seenNorms[$norm] = $true
        if ($bucket) { $seenBuckets[$bucket] = $true }
        [void]$merged.Add($e)
    }
    $delim = Get-MemorySectionDelimiterChar
    $out = ($merged -join "`n$delim`n") + "`n"
    if ($DryRun.IsPresent) {
        Write-Host ('[DRY] ' + $FilePath + ' - ' + $($merged.Count) + ' entries') -ForegroundColor DarkGray
        return
    }
    $dir = Split-Path -Parent $FilePath
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    Set-Content -LiteralPath $FilePath -Value $out -Encoding UTF8 -NoNewline
    Write-HermesOk $FilePath
}
