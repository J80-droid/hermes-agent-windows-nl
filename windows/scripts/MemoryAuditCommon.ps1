# Gedeelde helpers voor memory/trust E2E en audit_profile_memories.ps1
#Requires -Version 5.1

$script:MemoryIdentityAllowPatterns = @(
    'miniconda3[\\/]envs[\\/]hermes-env[\\/]python\.exe',
    'Documents[\\/]Hermes Knowledge',
    'Documents[\\/]Obsidian Vault',
    'AppData[\\/]Local[\\/]hermes',
    'data[\\/]lancedb[\\/]'
)

function Test-MemoryIdentityLineAllowed {
    param([string]$Line)
    if ([string]::IsNullOrWhiteSpace($Line)) { return $true }
    foreach ($pat in $script:MemoryIdentityAllowPatterns) {
        if ($Line -match $pat) { return $true }
    }
    return $false
}

function Test-MemoryIdentityLeak {
    param([string]$Line)
    if ([string]::IsNullOrWhiteSpace($Line)) { return $false }
    if (Test-MemoryIdentityLineAllowed -Line $Line) { return $false }
    if ($Line -match 'Jamel el Mourif') { return $true }
    if ($Line -match '(?i)\bel Mourif\b') { return $true }
    if ($Line -match '(?i)\bJamel\b') { return $true }
    return $false
}

function Test-MemoryFileIdentityLeaks {
    param(
        [string]$FilePath,
        [ref]$LeakLines
    )
    $leaks = [System.Collections.Generic.List[string]]::new()
    if (-not (Test-Path -LiteralPath $FilePath)) {
        $LeakLines.Value = @()
        return $false
    }
    $i = 0
    foreach ($line in Get-Content -LiteralPath $FilePath -Encoding UTF8) {
        $i++
        if (Test-MemoryIdentityLeak -Line $line) {
            $leaks.Add("${i}:$line")
        }
    }
    $LeakLines.Value = $leaks
    return ($leaks.Count -gt 0)
}

function Get-MemoryFileIdentityLeakLines {
    param([string]$FilePath)
    $leaks = $null
    [void](Test-MemoryFileIdentityLeaks -FilePath $FilePath -LeakLines ([ref]$leaks))
    if ($null -eq $leaks) { return @() }
    return @($leaks)
}

function Get-MemoryDoubleEncodedSectionMarker {
    return ([string][char]0x00C2 + [char]0x00A7)
}

function Get-MemorySectionMarker {
    return ([string][char]0x00A7)
}

function Test-MemoryDoubleEncoding {
    param([string]$Text)
    if ([string]::IsNullOrEmpty($Text)) { return $false }
    return $Text.Contains((Get-MemoryDoubleEncodedSectionMarker))
}

function Get-MemoryLimitsFromConfig {
    param([string]$ConfigPath)
    $result = @{
        MemoryCharLimit = 0
        UserCharLimit   = 0
        HasMemoryBlock  = $false
    }
    if (-not (Test-Path -LiteralPath $ConfigPath)) { return $result }
    $cfg = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8
    if ($cfg -notmatch '(?m)^\s*memory:\s*$') {
        return $result
    }
    $result.HasMemoryBlock = $true
    if ($cfg -match 'memory_char_limit:\s*(\d+)') {
        $result.MemoryCharLimit = [int]$Matches[1]
    }
    if ($cfg -match 'user_char_limit:\s*(\d+)') {
        $result.UserCharLimit = [int]$Matches[1]
    }
    return $result
}

function Test-ProfileMemoryConfigLimits {
    param(
        [string]$ConfigPath,
        [int]$MinMemory = 4000,
        [int]$MinUser = 1800
    )
    $lim = Get-MemoryLimitsFromConfig -ConfigPath $ConfigPath
    if (-not $lim.HasMemoryBlock) { return $false, 'memory: ontbreekt' }
    if ($lim.MemoryCharLimit -lt $MinMemory) {
        return $false, "memory_char_limit=$($lim.MemoryCharLimit) < $MinMemory"
    }
    if ($lim.UserCharLimit -lt $MinUser) {
        return $false, "user_char_limit=$($lim.UserCharLimit) < $MinUser"
    }
    return $true, "memory=$($lim.MemoryCharLimit) user=$($lim.UserCharLimit)"
}

function Test-AllProfileMemoryConfigLimits {
    param(
        [string]$HermesRoot,
        [int]$MinMemory = 4000,
        [int]$MinUser = 1800
    )
    $failures = [System.Collections.Generic.List[string]]::new()
    $rootCfg = Join-Path $HermesRoot 'config.yaml'
    if (Test-Path -LiteralPath $rootCfg) {
        $ok, $detail = Test-ProfileMemoryConfigLimits -ConfigPath $rootCfg -MinMemory $MinMemory -MinUser $MinUser
        if (-not $ok) { $failures.Add("root: $detail") }
    } else {
        $failures.Add('root: config.yaml ontbreekt')
    }
    $profilesDir = Join-Path $HermesRoot 'profiles'
    if (Test-Path -LiteralPath $profilesDir) {
        Get-ChildItem -LiteralPath $profilesDir -Directory | ForEach-Object {
            $cfg = Join-Path $_.FullName 'config.yaml'
            if (-not (Test-Path -LiteralPath $cfg)) {
                $failures.Add("$($_.Name): config.yaml ontbreekt")
                return
            }
            $ok, $detail = Test-ProfileMemoryConfigLimits -ConfigPath $cfg -MinMemory $MinMemory -MinUser $MinUser
            if (-not $ok) { $failures.Add("$($_.Name): $detail") }
        }
    }
    return $failures
}

function Get-MemorySectionHashes {
    param([string]$FilePath)
    if (-not (Test-Path -LiteralPath $FilePath)) { return @() }
    $raw = Get-Content -LiteralPath $FilePath -Raw -Encoding UTF8
    $sep = '(?:' + [regex]::Escape((Get-MemoryDoubleEncodedSectionMarker)) + '|' + [regex]::Escape((Get-MemorySectionMarker)) + ')'
    $parts = $raw -split $sep
    $hashes = [System.Collections.Generic.List[string]]::new()
    foreach ($part in $parts) {
        $norm = ($part.Trim() -replace '\s+', ' ').ToLowerInvariant()
        if ($norm.Length -gt 20) {
            $hashes.Add($norm)
        }
    }
    return $hashes
}

function Get-DuplicateMemorySections {
    param([string]$FilePath)
    $hashes = Get-MemorySectionHashes -FilePath $FilePath
    $seen = @{}
    $dups = [System.Collections.Generic.List[string]]::new()
    foreach ($h in $hashes) {
        if ($seen.ContainsKey($h)) {
            $preview = if ($h.Length -gt 60) { $h.Substring(0, 60) + '...' } else { $h }
            $dups.Add($preview)
        } else {
            $seen[$h] = $true
        }
    }
    return $dups
}

function Test-MemoryFileHasMojibakeLine {
    param([string]$Text)
    if ([string]::IsNullOrEmpty($Text)) { return $false }
    $lonelyC2 = [string][char]0x00C2
    $pattern = '(?m)^\s*' + [regex]::Escape($lonelyC2) + '\s*$'
    return ($Text -match $pattern)
}

function Test-AllProfileMemoryFileSizes {
    param([string]$HermesRoot)
    $failures = [System.Collections.Generic.List[string]]::new()
    $profilesDir = Join-Path $HermesRoot 'profiles'
    if (-not (Test-Path -LiteralPath $profilesDir)) {
        return @('profiles map ontbreekt')
    }
    Get-ChildItem -LiteralPath $profilesDir -Directory | ForEach-Object {
        $name = $_.Name
        $cfg = Join-Path $_.FullName 'config.yaml'
        $lim = Get-MemoryLimitsFromConfig -ConfigPath $cfg
        $memLimit = if ($lim.MemoryCharLimit -gt 0) { $lim.MemoryCharLimit } else { 4000 }
        $userLimit = if ($lim.UserCharLimit -gt 0) { $lim.UserCharLimit } else { 1800 }
        foreach ($file in @('MEMORY.md', 'USER.md')) {
            $path = Join-Path $_.FullName "memories\$file"
            if (-not (Test-Path -LiteralPath $path)) {
                $failures.Add("$name/$file ontbreekt")
                continue
            }
            $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8
            $cap = if ($file -eq 'MEMORY.md') { $memLimit } else { $userLimit }
            if ($raw.Length -gt $cap) {
                $failures.Add("$name/$file OVER $($raw.Length)/$cap")
            }
            if (Test-MemoryDoubleEncoding -Text $raw) {
                $failures.Add("$name/$file double-encoding")
            }
            if (Test-MemoryFileHasMojibakeLine -Text $raw) {
                $failures.Add("$name/$file mojibake-regel")
            }
            $dups = Get-DuplicateMemorySections -FilePath $path
            if ($dups.Count -gt 0) {
                $failures.Add("$name/$file dubbele-sectie($($dups.Count))")
            }
        }
    }
    return $failures
}
