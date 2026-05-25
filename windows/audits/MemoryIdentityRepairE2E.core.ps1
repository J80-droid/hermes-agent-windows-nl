# E2E: runtime identity repair + pre-audit hook (MemoryAuditCommon / Invoke-MemoryTrustPostSync).
param(
    [Parameter(Mandatory)]
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
. (Join-Path $RepoRoot 'windows\HermesShellCommon.ps1')
. (Join-Path $RepoRoot 'windows\scripts\MemoryAuditCommon.ps1')

$script:CoreFailures = 0

function Get-IdentityE2EMockMemoryConfigYaml {
    return (@(
        'memory:',
        '  memory_char_limit: 4000',
        '  user_char_limit: 1800'
    ) -join [Environment]::NewLine)
}

function Add-IdentityE2EStep {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    $suffix = if ($Detail) { ' - ' + $Detail } else { '' }
    if ($Ok) {
        Write-HermesOk ($Name + $suffix)
    } else {
        Write-HermesFail ($Name + $suffix)
        $script:CoreFailures++
    }
}

function New-IdentityE2EMockRuntime {
    param([string]$ParentDir)
    $root = Join-Path $ParentDir 'hermes'
    $coreMemDir = Join-Path $root 'profiles\core\memories'
    New-Item -ItemType Directory -Path $coreMemDir -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $root 'config.yaml') -Value 'model: test' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $root 'profiles\core\config.yaml') -Value (Get-IdentityE2EMockMemoryConfigYaml) -Encoding UTF8
    return $root
}

function Invoke-MemoryIdentityRepairE2ECore {
    param([string]$RepoRoot)

Write-HermesSection '--- MemoryIdentityRepair core: repo keten ---'
$required = @(
    'windows\scripts\MemoryAuditCommon.ps1',
    'windows\scripts\repair_runtime_identity.ps1',
    'windows\scripts\Invoke-MemoryTrustPostSync.ps1',
    'windows\scripts\audit_profile_memories.ps1',
    'windows\SYNC_TRUST_PROTOCOL.bat'
)
foreach ($rel in $required) {
    $full = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel
    Add-IdentityE2EStep $rel (Test-Path -LiteralPath $full)
}

$postSyncText = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows\scripts\Invoke-MemoryTrustPostSync.ps1')
Add-IdentityE2EStep 'post-sync pre-audit scrub' ($postSyncText -match 'Repair-HermesRuntimeIdentity')
Add-IdentityE2EStep 'post-sync audit HermesRoot' ($postSyncText -match 'HermesRuntimeRoot')

$protocolText = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows\SYNC_TRUST_PROTOCOL.bat')
Add-IdentityE2EStep 'protocol pre-runtime scrub' ($protocolText -match 'repair_runtime_identity')

Write-HermesSection '--- MemoryIdentityRepair core: line repair ---'
$isoParent = Join-Path $env:TEMP ('hermes_identity_e2e_' + [Guid]::NewGuid().ToString('n'))
try {
    $mockRoot = New-IdentityE2EMockRuntime -ParentDir $isoParent
    $coreMem = Join-Path $mockRoot 'profiles\core\memories\MEMORY.md'
    $pathOnly = 'Log: C:\Users\jamel\AppData\Local\hermes\state.db'
    $leakLine = 'Jamel el Mourif reviewed the dossier.'
    Set-Content -LiteralPath $coreMem -Value @($pathOnly, $leakLine) -Encoding UTF8

    Add-IdentityE2EStep 'leak detectie' ((Get-MemoryFileIdentityLeakLines -FilePath $coreMem).Count -eq 1)
    $lineFixed = Repair-HermesIdentityLine -Line $leakLine
    Add-IdentityE2EStep 'line scrub full name' ($lineFixed -eq 'J. reviewed the dossier.')
    Add-IdentityE2EStep 'path line unchanged' (-not (Test-MemoryIdentityLeak -Line $pathOnly))

    $missing = Repair-HermesIdentityInFile -FilePath (Join-Path $mockRoot 'missing.md')
    Add-IdentityE2EStep 'missing file no throw' ($missing.Changed -eq $false -and $missing.HitCount -eq 0)

    $repair = Repair-HermesRuntimeIdentity -HermesRoot $mockRoot -Quiet
    Add-IdentityE2EStep 'runtime repair changed files' ($repair.FilesChanged -ge 1)
    Add-IdentityE2EStep 'runtime repair clears leaks' ((Get-MemoryFileIdentityLeakLines -FilePath $coreMem).Count -eq 0)
    $repairAgain = Repair-HermesRuntimeIdentity -HermesRoot $mockRoot -Quiet
    Add-IdentityE2EStep 'runtime repair idempotent' ($repairAgain.FilesChanged -eq 0)

    $emptyHermesRoot = Join-Path $isoParent 'empty_hermes'
    New-Item -ItemType Directory -Path $emptyHermesRoot -Force | Out-Null
    $skippedRepair = Repair-HermesRuntimeIdentity -HermesRoot $emptyHermesRoot -Quiet
    Add-IdentityE2EStep 'geen config.yaml skip' ($skippedRepair.Skipped -eq $true)

    Write-HermesSection '--- MemoryIdentityRepair core: post-sync integratie ---'
    $mockRoot2 = New-IdentityE2EMockRuntime -ParentDir (Join-Path $isoParent 'postsync')
    $mem2 = Join-Path $mockRoot2 'profiles\core\memories\MEMORY.md'
    Set-Content -LiteralPath $mem2 -Value 'Note: Jamel approved strategy.' -Encoding UTF8

    $prevSkip = $env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB
    $prevPause = $env:HERMES_SKIP_PAUSE
    $env:HERMES_SKIP_PAUSE = '1'
    Remove-Item Env:\HERMES_SKIP_RUNTIME_IDENTITY_SCRUB -ErrorAction SilentlyContinue
    try {
        $postPs1 = Join-Path $RepoRoot 'windows\scripts\Invoke-MemoryTrustPostSync.ps1'
        & $postPs1 -RepoRoot $RepoRoot -HermesRuntimeRoot $mockRoot2 -SkipProductionGate -Quiet
        $postRc = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
        Add-IdentityE2EStep 'post-sync PASS na scrub' ($postRc -eq 0)
        Add-IdentityE2EStep 'MEMORY scrubbed in post-sync' (-not (Test-MemoryIdentityLeak -Line (Get-Content -LiteralPath $mem2 -Encoding UTF8 | Select-Object -First 1)))
    } finally {
        if ($null -eq $prevPause) {
            Remove-Item Env:\HERMES_SKIP_PAUSE -ErrorAction SilentlyContinue
        } else {
            $env:HERMES_SKIP_PAUSE = $prevPause
        }
        if ($null -eq $prevSkip) {
            Remove-Item Env:\HERMES_SKIP_RUNTIME_IDENTITY_SCRUB -ErrorAction SilentlyContinue
        } else {
            $env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB = $prevSkip
        }
    }

    $mockRoot3 = New-IdentityE2EMockRuntime -ParentDir (Join-Path $isoParent 'skip')
    $mem3 = Join-Path $mockRoot3 'profiles\core\memories\MEMORY.md'
    Set-Content -LiteralPath $mem3 -Value 'Still Jamel here.' -Encoding UTF8
    $env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB = '1'
    try {
        & $postPs1 -RepoRoot $RepoRoot -HermesRuntimeRoot $mockRoot3 -SkipProductionGate -Quiet
        $skipRc = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
        Add-IdentityE2EStep 'skip scrub audit FAIL' ($skipRc -ne 0)
    } finally {
        Remove-Item Env:\HERMES_SKIP_RUNTIME_IDENTITY_SCRUB -ErrorAction SilentlyContinue
    }
} finally {
    if (Test-Path -LiteralPath $isoParent) {
        Remove-Item -LiteralPath $isoParent -Recurse -Force -ErrorAction SilentlyContinue
    }
}

    return $script:CoreFailures
}

exit (Invoke-MemoryIdentityRepairE2ECore -RepoRoot $RepoRoot)
