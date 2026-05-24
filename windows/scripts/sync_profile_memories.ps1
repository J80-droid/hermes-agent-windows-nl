# Merge canonical Trust & Forensic memory seed into root + all profile memories/.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

function Get-HermesRoot {
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

function Get-SeedEntries {
    param([string]$SectionName)
    $seedPath = Join-Path $RepoRoot 'docs/templates/MEMORY_CANONICAL_SEED.md'
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
        if ($inSection -and $line -match '^## ') { break }
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
        Write-Error "Sectie niet gevonden of leeg in seed: $SectionName"
    }
    return $entries.ToArray()
}

function Normalize-MemorySectionEntry {
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

function Merge-MemoryFile {
    param(
        [string]$FilePath,
        [string[]]$SeedEntries,
        [switch]$DryRun
    )
    $existing = @()
    if (Test-Path -LiteralPath $FilePath) {
        $raw = Get-Content -LiteralPath $FilePath -Raw -Encoding UTF8
        if ($raw.Trim()) {
            $lonelyC2 = [string][char]0x00C2
            $mojibakeLine = '(?m)^\s*' + [regex]::Escape($lonelyC2) + '\s*$'
            $existing = @(
                $raw -split '(?m)^§\s*$' |
                    ForEach-Object { ($_ -replace $mojibakeLine, '').Trim() } |
                    Where-Object { $_ }
            )
        }
    }
    $merged = [System.Collections.Generic.List[string]]::new()
    $seenNorms = @{}
    $seenBuckets = @{}

    foreach ($e in $SeedEntries) {
        $norm = Normalize-MemorySectionEntry -Text $e
        if (-not $norm -or $seenNorms.ContainsKey($norm)) { continue }
        $seenNorms[$norm] = $true
        $bucket = Get-MemoryPolicyBucket -Norm $norm
        if ($bucket) { $seenBuckets[$bucket] = $true }
        [void]$merged.Add($e)
    }
    foreach ($e in $existing) {
        $norm = Normalize-MemorySectionEntry -Text $e
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
        $bucket = Get-MemoryPolicyBucket -Norm $norm
        if ($bucket -and $seenBuckets.ContainsKey($bucket)) { continue }
        $seenNorms[$norm] = $true
        if ($bucket) { $seenBuckets[$bucket] = $true }
        [void]$merged.Add($e)
    }
    $out = ($merged -join "`n§`n") + "`n"
    if ($DryRun.IsPresent) {
        Write-Host ('[DRY] ' + $FilePath + ' - ' + $($merged.Count) + ' entries') -ForegroundColor DarkGray
        return
    }
    $dir = Split-Path -Parent $FilePath
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    Set-Content -LiteralPath $FilePath -Value $out -Encoding UTF8 -NoNewline
    Write-Host ('[OK] ' + $FilePath) -ForegroundColor Green
}

$root = Get-HermesRoot -OverrideRoot $HermesRoot
$userSeed = Get-SeedEntries -SectionName 'USER.md'
$memorySeed = Get-SeedEntries -SectionName 'MEMORY.md'

$targets = @(
    @{ User = Join-Path $root 'memories/USER.md'; Memory = Join-Path $root 'memories/MEMORY.md' }
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
Write-Host '[INFO] Memory seed merge voltooid (profiel-scoped leidend bij actief profiel).' -ForegroundColor Cyan
