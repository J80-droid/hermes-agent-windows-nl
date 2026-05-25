# Gedeelde helpers voor memory/trust E2E en audit_profile_memories.ps1
#Requires -Version 5.1

# Dot-source HermesShellCommon.ps1 vóór dit bestand (Join-HermesRepoPath, Write-HermesOk).
# PSES: geen '[' of '}' in regex-literals — whitespace via Replace-loop.
# Allow-patterns: gebouwd met [char]47 (match ook Windows-paden na normalisatie).
$script:MemoryIdentitySlash = [char]47
$s = $script:MemoryIdentitySlash
$script:MemoryIdentityAllowPatterns = @(
    ('miniconda3' + $s + 'envs' + $s + 'hermes-env' + $s + 'python.exe'),
    ('Documents' + $s + 'Hermes Knowledge'),
    ('Documents' + $s + 'Obsidian Vault'),
    ('AppData' + $s + 'Local' + $s + 'hermes'),
    ('data' + $s + 'lancedb' + $s)
)

function Test-MemoryIdentityLineAllowed {
    param([string]$Line)
    if ([string]::IsNullOrWhiteSpace($Line)) { return $true }
    $slash = [char]47
    $back = [char]92
    $norm = $Line.Replace($back, $slash)
    $usersSeg = 'Users' + $slash
    $appDataSeg = $slash + 'AppData'
    if ($norm.Contains($usersSeg) -and $norm.Contains($appDataSeg)) { return $true }
    foreach ($pat in $script:MemoryIdentityAllowPatterns) {
        if ($norm.Contains($pat)) { return $true }
    }
    return $false
}

function Test-MemoryIdentityLeak {
    param([string]$Line)
    if ([string]::IsNullOrWhiteSpace($Line)) { return $false }
    if (Test-MemoryIdentityLineAllowed -Line $Line) { return $false }
    if ($Line -imatch 'jamel el mourif') { return $true }
    if ($Line -imatch 'el mourif') { return $true }
    if ($Line -imatch 'jamel') { return $true }
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
            $leaks.Add(($i.ToString() + ':' + $line))
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

function Repair-HermesIdentityLine {
    param([string]$Line)
    if (-not (Test-MemoryIdentityLeak -Line $Line)) { return $Line }
    $out = $Line
    $out = [regex]::Replace($out, 'Jamel el Mourif', 'J.', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    $out = [regex]::Replace($out, 'Jamel', 'J.', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    $out = [regex]::Replace($out, 'el Mourif', '', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    $out = $out.Replace([char]9, ' ')
    while ($out.Contains('  ')) {
        $out = $out.Replace('  ', ' ')
    }
    return $out.Trim()
}

function Repair-HermesIdentityInFile {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [switch]$DryRun
    )
    if (-not (Test-Path -LiteralPath $FilePath)) {
        return @{
            Changed  = $false
            HitCount = 0
            Error    = ''
        }
    }
    $lines = @(Get-Content -LiteralPath $FilePath -Encoding UTF8 -ErrorAction SilentlyContinue)
    if ($null -eq $lines -or $lines.Count -eq 0) {
        if (-not (Test-Path -LiteralPath $FilePath)) {
            return @{
                Changed  = $false
                HitCount = 0
                Error    = 'read failed'
            }
        }
    }
    $hitCount = 0
    $changed = $false
    $outLines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in $lines) {
        $repaired = Repair-HermesIdentityLine -Line $line
        if ($repaired -ne $line) {
            $hitCount++
            $changed = $true
        }
        [void]$outLines.Add($repaired)
    }
    if ($changed -and -not $DryRun) {
        Set-Content -LiteralPath $FilePath -Value $outLines -Encoding UTF8 -ErrorAction SilentlyContinue
        if (-not $?) {
            return @{
                Changed  = $false
                HitCount = $hitCount
                Error    = 'write failed'
            }
        }
    }
    return @{
        Changed  = $changed
        HitCount = $hitCount
        Error    = ''
    }
}

function Get-HermesRuntimeRoot {
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

function Get-HermesPersonaFilePaths {
    param([string]$HermesRoot)
    $list = [System.Collections.Generic.List[string]]::new()
    $slash = [char]47
    $rootRels = @('SOUL.md', ('memories' + $slash + 'USER.md'), ('memories' + $slash + 'MEMORY.md'))
    foreach ($rel in $rootRels) {
        $p = Join-HermesRepoPath -RepoRoot $HermesRoot -RelativePath $rel
        if (Test-Path -LiteralPath $p) { [void]$list.Add($p) }
    }
    $profilesDir = Join-HermesRepoPath -RepoRoot $HermesRoot -RelativePath 'profiles'
    if (Test-Path -LiteralPath $profilesDir) {
        Get-ChildItem -LiteralPath $profilesDir -Directory | ForEach-Object {
            $profileName = $_.Name
            foreach ($name in @('SOUL.md', 'LEGAL_ACTIVE_MATTERS.md')) {
                $profRel = 'profiles' + $slash + $profileName + $slash + $name
                $p = Join-HermesRepoPath -RepoRoot $HermesRoot -RelativePath $profRel
                if (Test-Path -LiteralPath $p) { [void]$list.Add($p) }
            }
            foreach ($memLeaf in @('USER.md', 'MEMORY.md')) {
                $memRel = 'profiles' + $slash + $profileName + $slash + 'memories' + $slash + $memLeaf
                $p = Join-HermesRepoPath -RepoRoot $HermesRoot -RelativePath $memRel
                if (Test-Path -LiteralPath $p) { [void]$list.Add($p) }
            }
        }
    }
    return @($list | Select-Object -Unique)
}

function Test-HermesScrubExcludedPath {
    param([string]$FullPath)
    $slash = [char]47
    $norm = $FullPath.Replace([char]92, $slash)
    $segments = @(
        ($slash + 'lancedb'),
        '.lance',
        ($slash + 'logs'),
        ($slash + '.git'),
        ($slash + 'website'),
        ($slash + 'node_modules'),
        ($slash + '__pycache__'),
        ($slash + 'backups'),
        ($slash + 'sessions'),
        ($slash + 'pastes'),
        ($slash + 'cache'),
        ($slash + 'state-snapshots'),
        ($slash + 'venv'),
        ($slash + 'skills'),
        '_trust_backup_',
        'scrub_identity_report.json',
        'scrub_identity_to_J.ps1',
        'repair_runtime_identity.ps1',
        'RUN_TRUST_FORENSIC_E2E.ps1'
    )
    foreach ($seg in $segments) {
        if ($norm.Contains($seg)) { return $true }
    }
    if ($norm.EndsWith('.env', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    return $false
}

function Get-HermesScrubTextExtensions {
    return @('.md', '.txt', '.yaml', '.yml', '.bat', '.json', '.csv', '.html', '.htm', '.xml', '.ini', '.example')
}

function Get-HermesScrubTargetFiles {
    param([string[]]$RootPaths)
    $files = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($rootPath in $RootPaths) {
        if (-not (Test-Path -LiteralPath $rootPath)) { continue }
        if ((Get-Item -LiteralPath $rootPath).PSIsContainer) {
            Get-ChildItem -LiteralPath $rootPath -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
                if (-not (Test-HermesScrubExcludedPath -FullPath $_.FullName)) {
                    [void]$files.Add($_.FullName)
                }
            }
        } elseif (-not (Test-HermesScrubExcludedPath -FullPath $rootPath)) {
            [void]$files.Add($rootPath)
        }
    }
    return @($files)
}

function Repair-HermesRuntimeIdentity {
    param(
        [string]$HermesRoot = '',
        [switch]$DryRun,
        [switch]$Quiet
    )
    if (-not $HermesRoot) {
        $HermesRoot = Get-HermesRuntimeRoot
    }
    if (-not (Test-Path -LiteralPath (Join-Path $HermesRoot 'config.yaml'))) {
        return @{
            FilesChanged = 0
            HitCount     = 0
            ChangedPaths = @()
            Skipped      = $true
            Reason       = 'geen config.yaml onder runtime root'
        }
    }
    $totalHits = 0
    $filesChanged = 0
    $changedPaths = [System.Collections.Generic.List[string]]::new()
    foreach ($filePath in (Get-HermesPersonaFilePaths -HermesRoot $HermesRoot)) {
        $result = Repair-HermesIdentityInFile -FilePath $filePath -DryRun:$DryRun
        $totalHits += $result.HitCount
        if ($result.Changed) {
            $filesChanged++
            $rel = $filePath
            if ($filePath.StartsWith($HermesRoot, [StringComparison]::OrdinalIgnoreCase)) {
                $rel = $filePath.Substring($HermesRoot.Length).TrimStart('\', '/')
            }
            [void]$changedPaths.Add($rel)
            if (-not $Quiet) {
                Write-HermesOk ('scrubbed: ' + $rel)
            }
        }
    }
    return @{
        FilesChanged = $filesChanged
        HitCount     = $totalHits
        ChangedPaths = @($changedPaths)
    }
}

function Repair-HermesRepoIdentity {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [switch]$DryRun,
        [switch]$Quiet
    )
    $textExtensions = Get-HermesScrubTextExtensions
    $targetFiles = Get-HermesScrubTargetFiles -RootPaths @(
        (Join-Path $RepoRoot 'docs'),
        (Join-Path $RepoRoot 'memory-bank'),
        (Join-Path $RepoRoot 'windows')
    )
    $totalHits = 0
    $filesChanged = 0
    $changedPaths = [System.Collections.Generic.List[string]]::new()
    foreach ($filePath in ($targetFiles | Select-Object -Unique)) {
        $ext = [IO.Path]::GetExtension($filePath).ToLowerInvariant()
        if ($textExtensions -notcontains $ext) { continue }
        $result = Repair-HermesIdentityInFile -FilePath $filePath -DryRun:$DryRun
        $totalHits += $result.HitCount
        if ($result.Changed) {
            $filesChanged++
            $rel = $filePath
            if ($filePath.StartsWith($RepoRoot, [StringComparison]::OrdinalIgnoreCase)) {
                $rel = $filePath.Substring($RepoRoot.Length).TrimStart('\', '/')
            }
            [void]$changedPaths.Add($rel)
            if (-not $Quiet) {
                Write-HermesOk ('repo scrubbed: ' + $rel)
            }
        }
    }
    return @{
        FilesChanged = $filesChanged
        HitCount     = $totalHits
        ChangedPaths = @($changedPaths)
    }
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
        $rootLimit = Test-ProfileMemoryConfigLimits -ConfigPath $rootCfg -MinMemory $MinMemory -MinUser $MinUser
        if (-not $rootLimit[0]) { $failures.Add('root: ' + $rootLimit[1]) }
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
            $profLimit = Test-ProfileMemoryConfigLimits -ConfigPath $cfg -MinMemory $MinMemory -MinUser $MinUser
            if (-not $profLimit[0]) { $failures.Add($_.Name + ': ' + $profLimit[1]) }
        }
    }
    return $failures
}

function Get-MemorySectionHashes {
    param([string]$FilePath)
    if (-not (Test-Path -LiteralPath $FilePath)) { return @() }
    $raw = Get-Content -LiteralPath $FilePath -Raw -Encoding UTF8
    $markerA = [regex]::Escape((Get-MemoryDoubleEncodedSectionMarker))
    $markerB = [regex]::Escape((Get-MemorySectionMarker))
    $splitPattern = $markerA + '|' + $markerB
    $parts = $raw -split $splitPattern
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
    $rootCfg = Join-Path $HermesRoot 'config.yaml'
    if (Test-Path -LiteralPath $rootCfg) {
        $limRoot = Get-MemoryLimitsFromConfig -ConfigPath $rootCfg
        $memLimitRoot = if ($limRoot.MemoryCharLimit -gt 0) { $limRoot.MemoryCharLimit } else { 4000 }
        $userLimitRoot = if ($limRoot.UserCharLimit -gt 0) { $limRoot.UserCharLimit } else { 1800 }
        foreach ($file in @('MEMORY.md', 'USER.md')) {
            $path = Join-Path $HermesRoot "memories\$file"
            if (-not (Test-Path -LiteralPath $path)) { continue }
            $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8
            $cap = if ($file -eq 'MEMORY.md') { $memLimitRoot } else { $userLimitRoot }
            if ($raw.Length -gt $cap) {
                $failures.Add("legacy-root/$file OVER $($raw.Length)/$cap")
            }
            if (Test-MemoryDoubleEncoding -Text $raw) {
                $failures.Add("legacy-root/$file double-encoding")
            }
            if (Test-MemoryFileHasMojibakeLine -Text $raw) {
                $failures.Add("legacy-root/$file mojibake-regel")
            }
            $dups = Get-DuplicateMemorySections -FilePath $path
            if ($dups.Count -gt 0) {
                $failures.Add("legacy-root/$file dubbele-sectie($($dups.Count))")
            }
        }
    }
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

$mergeCommonPath = Join-Path $PSScriptRoot 'HermesMemoryMergeCommon.ps1'
if (Test-Path -LiteralPath $mergeCommonPath) {
    . $mergeCommonPath
}

function Get-MemoryMarkdownSectionsFromFile {
    param([string]$FilePath)
    if (-not (Test-Path -LiteralPath $FilePath)) { return @() }
    $raw = Get-Content -LiteralPath $FilePath -Raw -Encoding UTF8
    return @(Split-MemoryMarkdownSections -Raw $raw)
}

function Test-MemoryConsolidationLayout {
    param([string]$HermesRoot)
    $failures = [System.Collections.Generic.List[string]]::new()

    $rootMemPath = Join-HermesRepoPath -RepoRoot $HermesRoot -RelativePath ('memories' + [char]47 + 'MEMORY.md')
    $rootSections = Get-MemoryMarkdownSectionsFromFile -FilePath $rootMemPath
    if ($rootSections.Count -gt 4) {
        [void]$failures.Add("root: $($rootSections.Count) MEMORY-secties (verwacht seed-only ~3)")
    }
    foreach ($sec in $rootSections) {
        $norm = ConvertTo-MemorySectionNormalized -Text $sec
        if (Get-MemoryPolicyBucket -Norm $norm) { continue }
        if (Test-MemoryLegalDomainSection -Text $sec) {
            [void]$failures.Add('root: legal-domein in legacy memories/')
        }
        if (Test-MemoryHermesConfigSection -Text $sec) {
            [void]$failures.Add('root: Hermes-config in legacy memories/')
        }
    }

    $s = [char]47
    $coreMemPath = Join-HermesRepoPath -RepoRoot $HermesRoot -RelativePath ('profiles' + $s + 'core' + $s + 'memories' + $s + 'MEMORY.md')
    $coreHasHermes = $false
    foreach ($sec in (Get-MemoryMarkdownSectionsFromFile -FilePath $coreMemPath)) {
        if (Test-MemoryHermesConfigSection -Text $sec) { $coreHasHermes = $true }
    }
    if (-not $coreHasHermes) {
        [void]$failures.Add('core: Hermes-config ontbreekt (MCP/multi-profile)')
    }

    $legalMemPath = Join-HermesRepoPath -RepoRoot $HermesRoot -RelativePath ('profiles' + $s + 'legal' + $s + 'memories' + $s + 'MEMORY.md')
    foreach ($sec in (Get-MemoryMarkdownSectionsFromFile -FilePath $legalMemPath)) {
        $norm = ConvertTo-MemorySectionNormalized -Text $sec
        if (Get-MemoryPolicyBucket -Norm $norm) { continue }
        if ((Test-MemoryHermesConfigSection -Text $sec) -and -not (Test-MemoryLegalDomainSection -Text $sec)) {
            [void]$failures.Add('legal: misplaatste Hermes-config')
            break
        }
    }

    $profilesDir = Join-Path $HermesRoot 'profiles'
    if (Test-Path -LiteralPath $profilesDir) {
        Get-ChildItem -LiteralPath $profilesDir -Directory | Where-Object {
            $_.Name -notin @('core', 'legal')
        } | ForEach-Object {
            $memPath = Join-Path $_.FullName 'memories/MEMORY.md'
            foreach ($sec in (Get-MemoryMarkdownSectionsFromFile -FilePath $memPath)) {
                $norm = ConvertTo-MemorySectionNormalized -Text $sec
                if (Get-MemoryPolicyBucket -Norm $norm) { continue }
                if (Test-MemoryLegalDomainSection -Text $sec) {
                    [void]$failures.Add("$($_.Name): legal-domein in niet-legal profiel")
                }
                if (Test-MemoryHermesConfigSection -Text $sec) {
                    [void]$failures.Add("$($_.Name): Hermes-config buiten core")
                }
            }
        }
    }

    return $failures
}
