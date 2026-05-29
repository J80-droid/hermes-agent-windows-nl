# Trim profile MEMORY.md / USER.md binnen config-limieten; backup vóór wijziging.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
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
$trimSuffix = '[... ingekort door Hermes memory limit ...]'
$memorySeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'MEMORY.md'
$userSeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'USER.md'
$seedNormsMem = @{}
foreach ($e in $memorySeed) { $seedNormsMem[(ConvertTo-MemorySectionNormalized -Text $e)] = $true }
$seedNormsUser = @{}
foreach ($e in $userSeed) { $seedNormsUser[(ConvertTo-MemorySectionNormalized -Text $e)] = $true }

function Test-IsProtectedMemorySection {
    param(
        [string]$Text,
        [string]$FileKind,
        [hashtable]$SeedNorms
    )
    if ([string]::IsNullOrWhiteSpace($Text)) { return $true }
    $norm = ConvertTo-MemorySectionNormalized -Text $Text
    if ($SeedNorms.ContainsKey($norm)) { return $true }
    if (Get-MemoryPolicyBucket -Norm $norm) { return $true }
    if (Test-MemoryRuntimeSection -Text $Text) { return $true }
    if ($FileKind -eq 'MEMORY.md' -and (Test-MemoryHermesConfigSection -Text $Text)) { return $true }
    if ($FileKind -eq 'USER.md' -and (Test-MemoryUserPreferenceSection -Text $Text)) { return $true }
    return $false
}

function Get-MemoryFileCharLimit {
    param(
        [string]$HermesRootPath,
        [string]$ProfileName,
        [string]$FileKind
    )
    if ($ProfileName -eq 'legacy-root') {
        $cfg = Join-Path $HermesRootPath 'config.yaml'
    } else {
        $cfg = Join-Path $HermesRootPath (Join-Path 'profiles' (Join-Path $ProfileName 'config.yaml'))
    }
    $lim = Get-MemoryLimitsFromConfig -ConfigPath $cfg
    if ($FileKind -eq 'MEMORY.md') {
        if ($lim.MemoryCharLimit -gt 0) { return $lim.MemoryCharLimit }
        return 4000
    }
    if ($lim.UserCharLimit -gt 0) { return $lim.UserCharLimit }
    return 1800
}

function Join-MemorySections {
    param([string[]]$Sections)
    $delim = Get-MemorySectionDelimiterChar
    if ($Sections.Count -eq 0) { return '' }
    return (($Sections -join "`n$delim`n") + "`n")
}

function Invoke-TrimMemoryFileToLimit {
    param(
        [string]$FilePath,
        [string]$FileKind,
        [hashtable]$SeedNorms,
        [int]$Cap,
        [switch]$DryRun
    )
    if (-not (Test-Path -LiteralPath $FilePath)) { return $true }
    $raw = Get-Content -LiteralPath $FilePath -Raw -Encoding UTF8
    if ($raw.Length -le $Cap) { return $true }

    $sections = [System.Collections.Generic.List[string]]::new()
    foreach ($sec in (Split-MemoryMarkdownSections -Raw $raw)) {
        [void]$sections.Add($sec)
    }

    function Get-Joined { param([string[]]$Arr) Join-MemorySections -Sections $Arr }

    $current = Get-Joined $sections.ToArray()
    while ($current.Length -gt $Cap) {
        $droppableIdx = -1
        $droppableLen = [int]::MaxValue
        for ($i = 0; $i -lt $sections.Count; $i++) {
            $sec = $sections[$i]
            if (Test-IsProtectedMemorySection -Text $sec -FileKind $FileKind -SeedNorms $SeedNorms) { continue }
            if ($sec.Length -lt $droppableLen) {
                $droppableLen = $sec.Length
                $droppableIdx = $i
            }
        }
        if ($droppableIdx -ge 0) {
            $sections.RemoveAt($droppableIdx)
            $current = Get-Joined $sections.ToArray()
            continue
        }

        $truncIdx = -1
        $truncLen = -1
        for ($i = 0; $i -lt $sections.Count; $i++) {
            $sec = $sections[$i]
            if (Test-IsProtectedMemorySection -Text $sec -FileKind $FileKind -SeedNorms $SeedNorms) { continue }
            if ($sec.Length -gt $truncLen) {
                $truncLen = $sec.Length
                $truncIdx = $i
            }
        }
        if ($truncIdx -lt 0) { return $false }

        $sec = $sections[$truncIdx]
        $baseLen = (Get-Joined @($sections.ToArray() | Where-Object { $_ -ne $sec })).Length
        $room = $Cap - $baseLen - 4
        if ($room -lt ($trimSuffix.Length + 40)) { return $false }
        $keep = [Math]::Min($sec.Length, $room - $trimSuffix.Length)
        $sections[$truncIdx] = $sec.Substring(0, $keep).TrimEnd() + "`n$trimSuffix"
        $current = Get-Joined $sections.ToArray()
        if ($current.Length -gt $Cap) { return $false }
        break
    }

    if (-not $DryRun) {
        Set-Content -LiteralPath $FilePath -Value $current -Encoding UTF8 -NoNewline
    }
    return $true
}

$targets = [System.Collections.Generic.List[object]]::new()
foreach ($file in @('MEMORY.md', 'USER.md')) {
    $p = Join-Path $root (Join-Path 'memories' $file)
    if (Test-Path -LiteralPath $p) {
        [void]$targets.Add(@{ Path = $p; Profile = 'legacy-root'; File = $file })
    }
}
$profilesDir = Join-Path $root 'profiles'
if (Test-Path -LiteralPath $profilesDir) {
    Get-ChildItem -LiteralPath $profilesDir -Directory | ForEach-Object {
        foreach ($file in @('MEMORY.md', 'USER.md')) {
            $p = Join-Path $_.FullName (Join-Path 'memories' $file)
            if (Test-Path -LiteralPath $p) {
                [void]$targets.Add(@{ Path = $p; Profile = $_.Name; File = $file })
            }
        }
    }
}

$backupRoot = $null
$anyChange = $false
$failures = [System.Collections.Generic.List[string]]::new()

foreach ($t in $targets) {
    $cap = Get-MemoryFileCharLimit -HermesRootPath $root -ProfileName $t.Profile -FileKind $t.File
    $raw = Get-Content -LiteralPath $t.Path -Raw -Encoding UTF8
    if ($raw.Length -le $cap) { continue }

    if (-not $backupRoot -and -not $DryRun) {
        $backupParent = Join-Path $env:LOCALAPPDATA 'hermes/backups'
        if (-not (Test-Path -LiteralPath $backupParent)) {
            New-Item -ItemType Directory -Path $backupParent -Force | Out-Null
        }
        $backupRoot = Join-Path $backupParent ('memory-trim-' + (Get-Date -Format 'yyyy-MM-dd_HHmmss'))
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    }
    if ($backupRoot -and -not $DryRun) {
        $rel = if ($t.Profile -eq 'legacy-root') {
            Join-Path 'memories' $t.File
        } else {
            Join-Path 'profiles' (Join-Path $t.Profile (Join-Path 'memories' $t.File))
        }
        $destDir = Split-Path -Parent (Join-Path $backupRoot $rel)
        if ($destDir -and -not (Test-Path -LiteralPath $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $t.Path -Destination (Join-Path $backupRoot $rel) -Force
    }

    $seedNorms = if ($t.File -eq 'MEMORY.md') { $seedNormsMem } else { $seedNormsUser }
    $ok = Invoke-TrimMemoryFileToLimit -FilePath $t.Path -FileKind $t.File -SeedNorms $seedNorms -Cap $cap -DryRun:$DryRun
    if ($ok) {
        $anyChange = $true
        if (-not $Quiet) {
            $newLen = if ($DryRun) { '<= ' + $cap } else { (Get-Content -LiteralPath $t.Path -Raw -Encoding UTF8).Length }
            Write-Host "[OK] $($t.Profile)/$($t.File) binnen limiet ($newLen/$cap)" -ForegroundColor Green
        }
    } else {
        $len = (Get-Content -LiteralPath $t.Path -Raw -Encoding UTF8).Length
        [void]$failures.Add("$($t.Profile)/$($t.File) OVER $len/$cap na trim")
    }
}

if ($failures.Count -gt 0) {
    foreach ($f in $failures) { Write-Host "[FAIL] $f" -ForegroundColor Red }
    exit 1
}

if ($anyChange -and $backupRoot -and -not $Quiet) {
    Write-Host "[OK] Backup: $backupRoot" -ForegroundColor Cyan
}
if (-not $Quiet -and -not $anyChange) {
    Write-Host '[OK] Geen profielen boven limiet.' -ForegroundColor Green
}
exit 0
