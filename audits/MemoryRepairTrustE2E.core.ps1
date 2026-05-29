# E2E: automatische memory-trim (enforce), repair-orchestrator, post-sync choke point, trust-stamp.
# Geen live netwerk; temp Hermes-root via -HermesRoot. Draai: audits\RUN_MEMORY_REPAIR_TRUST_E2E.bat
param(
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

. (Join-Path $RepoRoot 'windows/HermesShellCommon.ps1')
. (Join-Path $RepoRoot 'windows/scripts/HermesMemoryMergeCommon.ps1')
. (Join-Path $RepoRoot 'windows/scripts/MemoryAuditCommon.ps1')
Import-Module (Join-Path $RepoRoot 'windows/scripts/TrustRuntimeSync.psm1') -Force

$script:Failures = 0
$script:StepNum = 0
$script:StepTotal = 13

function Add-MemoryRepairTrustStep {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail = ''
    )
    $script:StepNum++
    $label = ('{0}/{1} {2}' -f $script:StepNum, $script:StepTotal, $Name)
    $suffix = if ($Detail) { ' - ' + $Detail } else { '' }
    if ($Ok) {
        Write-Host ('[OK] ' + $label + $suffix) -ForegroundColor Green
    } else {
        Write-Host ('[FAIL] ' + $label + $suffix) -ForegroundColor Red
        $script:Failures++
    }
}

function Get-MemoryRepairMockConfigYaml {
    return (@(
        'memory:',
        '  memory_char_limit: 4000',
        '  user_char_limit: 1800'
    ) -join [Environment]::NewLine)
}

function Join-MemoryRepairSections {
    param([string[]]$Sections)
    $delim = Get-MemorySectionDelimiterChar
    if ($Sections.Count -eq 0) { return '' }
    return (($Sections -join "`n$delim`n") + "`n")
}

function New-MemoryRepairMockHermesRoot {
    param(
        [Parameter(Mandatory)][string]$ParentDir,
        [Parameter(Mandatory)][string]$RepoRoot
    )
    $root = Join-Path $ParentDir 'hermes_mock'
    $coreMemDir = Join-Path $root 'profiles\core\memories'
    New-Item -ItemType Directory -Path $coreMemDir -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $root 'config.yaml') -Value 'model: test' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $root 'profiles\core\config.yaml') -Value (Get-MemoryRepairMockConfigYaml) -Encoding UTF8

    $userBody = @'
## USER preference
E2E user stub within limit.
'@
    Set-Content -LiteralPath (Join-Path $coreMemDir 'USER.md') -Value $userBody -Encoding UTF8

    $sections = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in (Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'MEMORY.md')) {
        [void]$sections.Add($entry)
    }
    [void]$sections.Add(@(
        '## Hermes-config',
        'multi-profile configuration E2E stub; Register MCP servers per-profile in docs.'
    ) -join "`n")

    $idx = 0
    do {
        [void]$sections.Add("## E2E bulk $idx`n" + ('z' * 700))
        $idx++
    } while ((Join-MemoryRepairSections -Sections $sections.ToArray()).Length -lt 5200)

    $memoryPath = Join-Path $coreMemDir 'MEMORY.md'
    Set-Content -LiteralPath $memoryPath -Value (Join-MemoryRepairSections -Sections $sections.ToArray()) -Encoding UTF8
    return @{
        Root       = $root
        MemoryPath = $memoryPath
    }
}

Write-Host '=== Memory Repair + Trust Stamp E2E ===' -ForegroundColor Cyan

$requiredPaths = @(
    'windows/scripts/enforce_profile_memory_char_limits.ps1',
    'windows/scripts/Invoke-RepairProfileMemoryLimits.ps1',
    'windows/scripts/Invoke-MemoryTrustPostSync.ps1',
    'windows/scripts/Invoke-TrustRuntimeLight.ps1',
    'windows/scripts/launch_trust_runtime_sync.ps1',
    'windows/scripts/TrustRuntimeSync.psm1',
    'windows/SYNC_TRUST_RUNTIME.bat',
    'windows/CONSOLIDATE_ROOT_MEMORIES.bat'
)
$pathsOk = $true
foreach ($rel in $requiredPaths) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $pathsOk = $false
        break
    }
}
Add-MemoryRepairTrustStep 'repo scripts en entrypoints' $pathsOk

$postSync = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/Invoke-MemoryTrustPostSync.ps1')
$trustBat = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/SYNC_TRUST_RUNTIME.bat')
$launchTrust = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_trust_runtime_sync.ps1')
$trustModule = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/TrustRuntimeSync.psm1')
$stampIdx = $launchTrust.IndexOf('Set-TrustRuntimeSyncStamp')
$auditIdx = $launchTrust.IndexOf('Test-TrustRuntimeMemoryAuditClean')
$pendingIdx = $launchTrust.IndexOf('Register-PendingTrustRuntimeRequired')
$wiringOk = ($postSync -match 'Invoke-RepairProfileMemoryLimits') -and
    ($postSync -match '-EnforceOnly') -and
    ($trustBat -match 'Invoke-RepairProfileMemoryLimits') -and
    ($trustBat -match 'Invoke-MemoryTrustPostSync') -and
    ($launchTrust -match 'Test-TrustRuntimeMemoryAuditClean') -and
    ($launchTrust -match 'Register-PendingTrustRuntimeRequired') -and
    ($trustModule -match 'enforce_profile_memory_char_limits\.ps1') -and
    ($pendingIdx -ge 0) -and
    ($auditIdx -ge 0) -and
    ($stampIdx -gt $auditIdx)
Add-MemoryRepairTrustStep 'keten wiring (post-sync, stamp, watch)' $wiringOk

$mergeCommon = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/HermesMemoryMergeCommon.ps1')
$repairText = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/Invoke-RepairProfileMemoryLimits.ps1')
Add-MemoryRepairTrustStep 'Ensure-HermesLegacyRootMemorySeed wiring' (
    ($mergeCommon -match 'function Ensure-HermesLegacyRootMemorySeed') -and
    ($repairText -match 'Ensure-HermesLegacyRootMemorySeed')
)

$critical = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/HermesCriticalWindowsRepoPaths.ps1')
Add-MemoryRepairTrustStep 'HermesCriticalWindowsRepoPaths' (
    ($critical -match 'enforce_profile_memory_char_limits\.ps1') -and
    ($critical -match 'Invoke-RepairProfileMemoryLimits\.ps1')
)

$watch = Get-TrustRuntimeWatchPaths -RepoRoot $RepoRoot
$watchOk = ($watch | Where-Object { $_ -match 'enforce_profile_memory_char_limits\.ps1' }).Count -ge 1 -and
    ($watch | Where-Object { $_ -match 'Invoke-RepairProfileMemoryLimits\.ps1' }).Count -ge 1
Add-MemoryRepairTrustStep 'TrustRuntimeSync watch-paden' $watchOk ("$($watch.Count) paden")

$repairPs1 = Join-Path $RepoRoot 'windows/scripts/Invoke-RepairProfileMemoryLimits.ps1'
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $repairPs1 -RepoRoot $RepoRoot -MigrateOnly -EnforceOnly *> $null
$conflictRc = $LASTEXITCODE
$ErrorActionPreference = $prevEap
Add-MemoryRepairTrustStep 'repair conflicterende vlaggen geweigerd' ($conflictRc -ne 0) ("exit=$conflictRc")

$isoParent = Join-Path $env:TEMP ('mem_repair_trust_e2e_' + [Guid]::NewGuid().ToString('n'))
try {
    $mock = New-MemoryRepairMockHermesRoot -ParentDir $isoParent -RepoRoot $RepoRoot
    $mockRoot = $mock.Root
    $memPath = $mock.MemoryPath

    $beforeLen = (Get-Content -LiteralPath $memPath -Raw -Encoding UTF8).Length
    $dirtyBefore = -not (Test-TrustRuntimeMemoryAuditClean -HermesRoot $mockRoot)
    Add-MemoryRepairTrustStep 'fixture OVER voor enforce' (($beforeLen -gt 4000) -and $dirtyBefore) ("len=$beforeLen")

    $enforcePs1 = Join-Path $RepoRoot 'windows/scripts/enforce_profile_memory_char_limits.ps1'
    & $enforcePs1 -RepoRoot $RepoRoot -HermesRoot $mockRoot -Quiet
    $enforceRc = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
    $afterLen = (Get-Content -LiteralPath $memPath -Raw -Encoding UTF8).Length
    $cleanAfterEnforce = Test-TrustRuntimeMemoryAuditClean -HermesRoot $mockRoot
    Add-MemoryRepairTrustStep 'enforce trim + schone audit' (
        ($enforceRc -eq 0) -and ($afterLen -le 4000) -and $cleanAfterEnforce
    ) ("$beforeLen -> $afterLen")

    $hermesStill = $false
    foreach ($sec in (Get-MemoryMarkdownSectionsFromFile -FilePath $memPath)) {
        if (Test-MemoryHermesConfigSection -Text $sec) { $hermesStill = $true }
    }
    Add-MemoryRepairTrustStep 'Hermes-config sectie behouden' $hermesStill

    $repairOut = & $repairPs1 -RepoRoot $RepoRoot -HermesRoot $mockRoot -EnforceOnly -Quiet 2>&1 | Out-String
    $repairRc = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
    $dedupOnMock = $repairOut -match [regex]::Escape($mockRoot)
    Add-MemoryRepairTrustStep 'Invoke-RepairProfileMemoryLimits -EnforceOnly' (
        ($repairRc -eq 0) -and $dedupOnMock -and (Test-TrustRuntimeMemoryAuditClean -HermesRoot $mockRoot)
    ) $(if ($dedupOnMock) { 'mock root' } else { 'dedup raakte productie-root' })

    $prevPause = $env:HERMES_SKIP_PAUSE
    $env:HERMES_SKIP_PAUSE = '1'
    try {
        $postPs1 = Join-Path $RepoRoot 'windows/scripts/Invoke-MemoryTrustPostSync.ps1'
        & $postPs1 -RepoRoot $RepoRoot -HermesRuntimeRoot $mockRoot -SkipProductionGate -Quiet
        $postRc = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
        Add-MemoryRepairTrustStep 'Invoke-MemoryTrustPostSync op mock root' ($postRc -eq 0)
    } finally {
        if ($null -eq $prevPause) {
            Remove-Item Env:\HERMES_SKIP_PAUSE -ErrorAction SilentlyContinue
        } else {
            $env:HERMES_SKIP_PAUSE = $prevPause
        }
    }

    $consolidateBat = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/CONSOLIDATE_ROOT_MEMORIES.bat')
    Add-MemoryRepairTrustStep 'CONSOLIDATE_ROOT_MEMORIES -Full' ($consolidateBat -match 'Invoke-RepairProfileMemoryLimits' -and $consolidateBat -match '-Full')

    $legacyRoot = Join-Path $mockRoot 'memories'
    $legacyUser = Join-Path $legacyRoot 'USER.md'
    $legacyMem = Join-Path $legacyRoot 'MEMORY.md'
    if (Test-Path -LiteralPath $legacyUser) { Remove-Item -LiteralPath $legacyUser -Force }
    if (Test-Path -LiteralPath $legacyMem) { Remove-Item -LiteralPath $legacyMem -Force }
    Ensure-HermesLegacyRootMemorySeed -HermesRoot $mockRoot -RepoRoot $RepoRoot
    $legacyOk = (Test-Path -LiteralPath $legacyUser) -and (Test-Path -LiteralPath $legacyMem)
    Add-MemoryRepairTrustStep 'legacy root seed bootstrap' $legacyOk
} finally {
    if (Test-Path -LiteralPath $isoParent) {
        Remove-Item -LiteralPath $isoParent -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ''
if ($script:Failures -gt 0) {
    Write-Host ('=== Memory Repair Trust E2E FAIL ({0} stap(pen)) ===' -f $script:Failures) -ForegroundColor Red
    exit 1
}
Write-Host ('=== Memory Repair Trust E2E PASS ({0}/{0}) ===' -f $script:StepTotal) -ForegroundColor Green
exit 0
