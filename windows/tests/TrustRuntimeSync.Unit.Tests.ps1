# Unit tests: TrustRuntimeSync.psm1 (geïsoleerde LOCALAPPDATA + temp repo; geen live sync/API).
# Draai: powershell -NoProfile -ExecutionPolicy Bypass -File windows/tests/TrustRuntimeSync.Unit.Tests.ps1
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$psm1 = Join-Path $repoRoot 'windows/scripts/TrustRuntimeSync.psm1'

$script:DomainProfiles = @(
    'core', 'legal', 'academics', 'operations', 'trading', 'gaming',
    'philosophy', 'logistics', 'ventures', 'ict', 'security', 'dev', 'data', 'creative'
)

$script:UnitFailed = 0
$isoLocal = Join-Path $env:TEMP ('trust_sync_unit_' + [Guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $isoLocal -Force | Out-Null
$prevLocal = $env:LOCALAPPDATA
$prevForceSync = $env:HERMES_FORCE_TRUST_SYNC
$env:LOCALAPPDATA = $isoLocal

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        Write-Host ('FAIL: ' + $Message) -ForegroundColor Red
        $script:UnitFailed++
    }
}

function Assert-False {
    param([bool]$Condition, [string]$Message)
    Assert-True (-not $Condition) $Message
}

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) {
        Write-Host ('FAIL: ' + $Message + " (expected='$Expected' actual='$Actual')") -ForegroundColor Red
        $script:UnitFailed++
    }
}

function Get-TrustSyncMockConfigYaml {
    param(
        [int]$MemoryLimit = 4000,
        [int]$UserLimit = 1800
    )
    return (@(
        'memory:',
        ('  memory_char_limit: ' + $MemoryLimit),
        ('  user_char_limit: ' + $UserLimit)
    ) -join [Environment]::NewLine)
}

function New-TrustSyncMockHermesRoot {
    param(
        [Parameter(Mandatory)][string]$ParentDir,
        [string[]]$Profiles = @('core'),
        [switch]$AllDomainProfiles,
        [switch]$OverCoreMemory,
        [switch]$WithIdentityLeak,
        [switch]$MissingUserForCore
    )
    if ($AllDomainProfiles) {
        $Profiles = $script:DomainProfiles
    }
    $root = Join-Path $ParentDir 'hermes'
    New-Item -ItemType Directory -Path $root -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $root 'config.yaml') -Value 'model: unit-test' -Encoding UTF8

    foreach ($profile in $Profiles) {
        $memDir = Join-Path $root (Join-Path 'profiles' (Join-Path $profile 'memories'))
        New-Item -ItemType Directory -Path $memDir -Force | Out-Null
        Set-Content -LiteralPath (Join-Path (Split-Path -Parent $memDir) 'config.yaml') -Value (Get-TrustSyncMockConfigYaml) -Encoding UTF8

        $memBody = "## Seed`nUnit test memory stub."
        if ($profile -eq 'core' -and $OverCoreMemory) {
            $memBody = "## Hermes-config`nmulti-profile configuration stub for unit tests.`n" + ('x' * 5000)
        }
        if ($profile -eq 'core' -and $WithIdentityLeak) {
            $memBody = 'Jamel wrote a note without scrub.'
        }
        Set-Content -LiteralPath (Join-Path $memDir 'MEMORY.md') -Value $memBody -Encoding UTF8

        if (-not ($profile -eq 'core' -and $MissingUserForCore)) {
            Set-Content -LiteralPath (Join-Path $memDir 'USER.md') -Value "## USER`nunit stub" -Encoding UTF8
        }
    }
    return $root
}

function New-TrustSyncMiniRepo {
    param([Parameter(Mandatory)][string]$ParentDir)
    $mini = Join-Path $ParentDir 'mini_repo'
    $seedSrc = Join-Path $repoRoot 'docs/templates/MEMORY_CANONICAL_SEED.md'
    $enforceSrc = Join-Path $repoRoot 'windows/scripts/enforce_profile_memory_char_limits.ps1'
    $seedDest = Join-Path $mini 'docs/templates/MEMORY_CANONICAL_SEED.md'
    $enforceDest = Join-Path $mini 'windows/scripts/enforce_profile_memory_char_limits.ps1'
    New-Item -ItemType Directory -Path (Split-Path -Parent $seedDest) -Force | Out-Null
    New-Item -ItemType Directory -Path (Split-Path -Parent $enforceDest) -Force | Out-Null
    Copy-Item -LiteralPath $seedSrc -Destination $seedDest -Force
    Copy-Item -LiteralPath $enforceSrc -Destination $enforceDest -Force
    return (Resolve-Path -LiteralPath $mini).Path
}

try {
    Import-Module $psm1 -Force

    $script:MockHermes = Join-Path $isoLocal 'hermes'
    New-Item -ItemType Directory -Path $script:MockHermes -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $script:MockHermes 'config.yaml') -Value 'model: unit-test' -Encoding UTF8

    # --- Happy path: stamp ---
    $hermesOnly = New-TrustSyncMockHermesRoot -ParentDir (Join-Path $isoLocal 'stamp_happy') -Profiles @('core')
    $stampPath = Join-Path $hermesOnly 'trust_runtime_sync.stamp'
    Set-TrustRuntimeSyncStamp -StampPath $stampPath
    Assert-True (Test-Path -LiteralPath $stampPath) 'Set-TrustRuntimeSyncStamp creates file'
    $stampText = [System.IO.File]::ReadAllText($stampPath)
    Assert-True ($stampText -match '^\d{4}-\d{2}-\d{2}') 'stamp bevat ISO-datum'

    $nestedStamp = Join-Path $hermesOnly 'stamps/nested/trust_runtime_sync.stamp'
    Set-TrustRuntimeSyncStamp -StampPath $nestedStamp
    Assert-True (Test-Path -LiteralPath $nestedStamp) 'Set-TrustRuntimeSyncStamp maakt parent dirs'

    $defaultStamp = Get-TrustRuntimeSyncStampPath
    Assert-True ($defaultStamp -match 'trust_runtime_sync\.stamp$') 'Get-TrustRuntimeSyncStampPath suffix'
    Assert-True ($defaultStamp.StartsWith($script:MockHermes)) 'stamp pad onder LOCALAPPDATA\hermes'

    # --- Watch paths (echte repo, read-only) ---
    $watch = Get-TrustRuntimeWatchPaths -RepoRoot $repoRoot
    Assert-True ($watch.Count -ge 5) 'watch-paden niet leeg'
    Assert-True (($watch | Where-Object { $_ -match 'enforce_profile_memory_char_limits\.ps1' }).Count -ge 1) 'watch bevat enforce script'
    Assert-True (($watch | Where-Object { $_ -match 'Invoke-RepairProfileMemoryLimits\.ps1' }).Count -ge 1) 'watch bevat repair script'

    $miniRepo = New-TrustSyncMiniRepo -ParentDir (Join-Path $isoLocal 'mini')
    $miniWatch = Get-TrustRuntimeWatchPaths -RepoRoot $miniRepo
    Assert-True ($miniWatch.Count -ge 2) 'mini repo watch-paden'

    # --- Profile completeness ---
    $partial = New-TrustSyncMockHermesRoot -ParentDir (Join-Path $isoLocal 'partial') -Profiles @('core')
    Assert-False (Test-TrustRuntimeProfileMemoriesComplete -HermesRoot $partial) 'alleen core is onvolledig t.o.v. 14 profielen'

    $missingUser = New-TrustSyncMockHermesRoot -ParentDir (Join-Path $isoLocal 'nouser') -Profiles @('core') -MissingUserForCore
    Assert-False (Test-TrustRuntimeProfileMemoriesComplete -HermesRoot $missingUser) 'ontbrekende USER.md'

    $allProfiles = New-TrustSyncMockHermesRoot -ParentDir (Join-Path $isoLocal 'allprof') -AllDomainProfiles
    Assert-True (Test-TrustRuntimeProfileMemoriesComplete -HermesRoot $allProfiles) 'alle domeinprofielen compleet'

    # --- Memory audit clean ---
    Assert-False (Test-TrustRuntimeMemoryAuditClean -HermesRoot (Join-Path $isoLocal 'nope_hermes')) 'geen profiles-dir'

    $overMem = New-TrustSyncMockHermesRoot -ParentDir (Join-Path $isoLocal 'over') -Profiles @('core') -OverCoreMemory
    Assert-False (Test-TrustRuntimeMemoryAuditClean -HermesRoot $overMem) 'OVER memory niet schoon'

    $leakMem = New-TrustSyncMockHermesRoot -ParentDir (Join-Path $isoLocal 'leak') -Profiles @('core') -WithIdentityLeak
    Assert-False (Test-TrustRuntimeMemoryAuditClean -HermesRoot $leakMem) 'identity leak niet schoon'

    $cleanCore = New-TrustSyncMockHermesRoot -ParentDir (Join-Path $isoLocal 'clean') -Profiles @('core')
    Assert-True (Test-TrustRuntimeMemoryAuditClean -HermesRoot $cleanCore) 'kleine core memory schoon'

    $zeroCapDir = Join-Path $isoLocal 'zerocap'
    $zeroRoot = New-TrustSyncMockHermesRoot -ParentDir $zeroCapDir -Profiles @('core')
    $zeroCfg = Join-Path $zeroRoot 'profiles/core/config.yaml'
    Set-Content -LiteralPath $zeroCfg -Value (@(
        'memory:',
        '  memory_char_limit: 0',
        '  user_char_limit: 0'
    ) -join "`n") -Encoding UTF8
    $smallMem = "## x`n" + ('a' * 100)
    Set-Content -LiteralPath (Join-Path $zeroRoot 'profiles/core/memories/MEMORY.md') -Value $smallMem -Encoding UTF8
    Assert-True (Test-TrustRuntimeMemoryAuditClean -HermesRoot $zeroRoot) 'cap 0 valt terug op defaults'

    $missingMemFile = New-TrustSyncMockHermesRoot -ParentDir (Join-Path $isoLocal 'missmem') -Profiles @('core')
    Remove-Item -LiteralPath (Join-Path $missingMemFile 'profiles/core/memories/MEMORY.md') -Force
    Assert-False (Test-TrustRuntimeMemoryAuditClean -HermesRoot $missingMemFile) 'ontbrekend MEMORY.md telt als issue'

    # --- Test-TrustRuntimeSyncNeeded ---
    Assert-True (Test-TrustRuntimeSyncNeeded -RepoRoot $repoRoot -Force) 'Force schakelaar'
    $env:HERMES_FORCE_TRUST_SYNC = '1'
    Assert-True (Test-TrustRuntimeSyncNeeded -RepoRoot $repoRoot) 'HERMES_FORCE_TRUST_SYNC=1'
    Remove-Item Env:\HERMES_FORCE_TRUST_SYNC -ErrorAction SilentlyContinue

    Remove-Item -LiteralPath (Join-Path $script:MockHermes 'profiles') -Recurse -Force -ErrorAction SilentlyContinue
    Assert-True (Test-TrustRuntimeSyncNeeded -RepoRoot $repoRoot) 'sync nodig bij onvolledige runtime (geen profielen)'

    $readyRoot = New-TrustSyncMockHermesRoot -ParentDir $isoLocal -AllDomainProfiles
    Assert-Equal $script:MockHermes $readyRoot 'mock root onder LOCALAPPDATA\hermes'

    $driftStamp = Join-Path $readyRoot 'trust_runtime_sync.stamp'
    Set-TrustRuntimeSyncStamp -StampPath $driftStamp
    Start-Sleep -Milliseconds 50
    Assert-False (Test-TrustRuntimeSyncNeeded -RepoRoot $miniRepo -StampPath $driftStamp) 'geen sync bij verse stamp + schone audit'

    [System.IO.File]::SetLastWriteTimeUtc($driftStamp, [datetime]::UtcNow.AddDays(-1))
    $touchTarget = Join-Path $miniRepo 'windows/scripts/enforce_profile_memory_char_limits.ps1'
    [System.IO.File]::SetLastWriteTimeUtc($touchTarget, [datetime]::UtcNow)
    Assert-True (Test-TrustRuntimeSyncNeeded -RepoRoot $miniRepo -StampPath $driftStamp) 'sync bij nieuwer watch-bestand'

    $bogusStamp = Join-Path $isoLocal 'no_stamp_yet/trust_runtime_sync.stamp'
    Assert-True (Test-TrustRuntimeSyncNeeded -RepoRoot $miniRepo -StampPath $bogusStamp) 'sync zonder stamp-bestand'

    # Negatief: ongeldige RepoRoot
    $badRepoThrown = $false
    try {
        [void](Get-TrustRuntimeWatchPaths -RepoRoot 'Z:\definitely_not_a_hermes_repo_path_12345')
    } catch {
        $badRepoThrown = $true
    }
    Assert-True $badRepoThrown 'ongeldige RepoRoot gooit bij Resolve-Path'

} finally {
    if ($null -eq $prevLocal) {
        Remove-Item -Path env:LOCALAPPDATA -ErrorAction SilentlyContinue
    } else {
        $env:LOCALAPPDATA = $prevLocal
    }
    if ($null -eq $prevForceSync) {
        Remove-Item Env:\HERMES_FORCE_TRUST_SYNC -ErrorAction SilentlyContinue
    } else {
        $env:HERMES_FORCE_TRUST_SYNC = $prevForceSync
    }
    Remove-Item -LiteralPath $isoLocal -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Module TrustRuntimeSync -ErrorAction SilentlyContinue
}

if ($script:UnitFailed -gt 0) {
    Write-Host ('TrustRuntimeSync unit tests FAILED: ' + $script:UnitFailed) -ForegroundColor Red
    exit 1
}
Write-Host 'TrustRuntimeSync unit tests: PASS' -ForegroundColor Green
exit 0
