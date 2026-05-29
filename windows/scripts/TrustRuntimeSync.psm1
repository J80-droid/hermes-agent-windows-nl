# Stamp + drift voor trust/memory sync bij start (equivalent SYNC_TRUST_RUNTIME.bat, zonder volledige audit-poort).
#Requires -Version 5.1

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

function Get-TrustRuntimeHermesRoot {
    Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force
    return Get-HermesRoot
}

function Get-TrustRuntimeSyncStampPath {
    $stampDir = Get-TrustRuntimeHermesRoot
    return Join-Path $stampDir 'trust_runtime_sync.stamp'
}

function Get-TrustRuntimeWatchPaths {
    param([Parameter(Mandatory)][string]$RepoRoot)
    $root = (Resolve-Path -LiteralPath $RepoRoot).Path
    $paths = [System.Collections.Generic.List[string]]::new()
    foreach ($rel in @(
            'docs/templates/MEMORY_CANONICAL_SEED.md',
            'docs/templates/SOUL_SHARED_VALUES.md',
            'docs/templates/SOUL_SHARED_TRUST_VERIFICATION.md',
            'docs/templates/SOUL_SHARED_TOOL_GOVERNANCE.md',
            'docs/templates/SOUL_LEGAL_DOMAIN.md',
            'docs/domain_toolsets.yaml',
            'windows/scripts/sync_profile_memories.ps1',
            'windows/scripts/invoke_deduplicate_memories.ps1',
            'windows/scripts/apply_trust_memory_limits.ps1',
            'windows/scripts/Invoke-TrustRuntimeLight.ps1',
            'windows/scripts/Invoke-MemoryTrustPostSync.ps1',
            'windows/scripts/sync_legal_soul_from_template.ps1',
            'windows/scripts/HermesMemoryMergeCommon.ps1',
            'windows/scripts/MemoryAuditCommon.ps1'
        )) {
        $p = Join-Path $root ($rel -replace '/', [char]92)
        if (Test-Path -LiteralPath $p) { [void]$paths.Add($p) }
    }
    $tplDir = Join-Path $root 'docs/templates'
    if (Test-Path -LiteralPath $tplDir) {
        Get-ChildItem -LiteralPath $tplDir -Filter 'SOUL_SHARED_*.md' -File -ErrorAction SilentlyContinue | ForEach-Object {
            [void]$paths.Add($_.FullName)
        }
    }
    return @($paths)
}

function Test-TrustRuntimeProfileMemoriesComplete {
    param([Parameter(Mandatory)][string]$HermesRoot)
    Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force
    foreach ($profile in Get-DomainSoulProfileNames) {
        $memDir = Join-Path $HermesRoot (Join-Path 'profiles' (Join-Path $profile 'memories'))
        foreach ($file in @('MEMORY.md', 'USER.md')) {
            $path = Join-Path $memDir $file
            if (-not (Test-Path -LiteralPath $path)) {
                return $false
            }
        }
    }
    return $true
}

function Test-TrustRuntimeMemoryAuditClean {
    param([Parameter(Mandatory)][string]$HermesRoot)
    . (Join-Path $PSScriptRoot 'MemoryAuditCommon.ps1')
    $profilesDir = Join-Path $HermesRoot 'profiles'
    if (-not (Test-Path -LiteralPath $profilesDir)) { return $false }
    $issues = 0
    foreach ($dir in Get-ChildItem -LiteralPath $profilesDir -Directory) {
        $cfg = Join-Path $dir.FullName 'config.yaml'
        $lim = Get-MemoryLimitsFromConfig -ConfigPath $cfg
        foreach ($file in @('MEMORY.md', 'USER.md')) {
            $path = Join-Path $dir.FullName (Join-Path 'memories' $file)
            if (-not (Test-Path -LiteralPath $path)) {
                $issues++
                continue
            }
            $len = (Get-Content -LiteralPath $path -Raw -Encoding UTF8).Length
            $cap = if ($file -eq 'MEMORY.md') { $lim.MemoryCharLimit } else { $lim.UserCharLimit }
            if ($len -gt $cap) { $issues++ }
            $leaks = $null
            if ($file -eq 'MEMORY.md' -and (Test-MemoryFileIdentityLeaks -FilePath $path -LeakLines ([ref]$leaks))) {
                $issues++
            }
        }
    }
    return ($issues -eq 0)
}

function Test-TrustRuntimeSyncNeeded {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$StampPath = '',
        [switch]$Force
    )
    if ($Force -or $env:HERMES_FORCE_TRUST_SYNC -eq '1') { return $true }
    $hermesRoot = Get-TrustRuntimeHermesRoot
    if (-not (Test-TrustRuntimeProfileMemoriesComplete -HermesRoot $hermesRoot)) {
        return $true
    }
    if (-not (Test-TrustRuntimeMemoryAuditClean -HermesRoot $hermesRoot)) {
        return $true
    }
    $stamp = if ($StampPath) { $StampPath } else { Get-TrustRuntimeSyncStampPath }
    if (-not (Test-Path -LiteralPath $stamp)) { return $true }
    $stampTime = (Get-Item -LiteralPath $stamp).LastWriteTimeUtc
    foreach ($f in Get-TrustRuntimeWatchPaths -RepoRoot $RepoRoot) {
        if ((Get-Item -LiteralPath $f).LastWriteTimeUtc -gt $stampTime) {
            return $true
        }
    }
    return $false
}

function Set-TrustRuntimeSyncStamp {
    param([string]$StampPath = '')
    $stamp = if ($StampPath) { $StampPath } else { Get-TrustRuntimeSyncStampPath }
    $dir = Split-Path -Parent $stamp
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($stamp, (Get-Date -Format 'o'), $utf8)
}

Export-ModuleMember -Function @(
    'Get-TrustRuntimeHermesRoot',
    'Get-TrustRuntimeSyncStampPath',
    'Get-TrustRuntimeWatchPaths',
    'Test-TrustRuntimeSyncNeeded',
    'Set-TrustRuntimeSyncStamp',
    'Test-TrustRuntimeProfileMemoriesComplete',
    'Test-TrustRuntimeMemoryAuditClean'
)
