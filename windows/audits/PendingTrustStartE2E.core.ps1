# Isolated E2E steps for pending trust-runtime at start (temp LOCALAPPDATA).
param(
    [Parameter(Mandatory)]
    [string]$RepoRoot,
    [Parameter(Mandatory)]
    [string]$IsolatedHermesDir
)

$ErrorActionPreference = 'Stop'
$script:CoreFailures = 0

function Add-PendingTrustE2EStep {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    $suffix = ''
    if ($Detail) { $suffix = ' - ' + $Detail }
    if ($Ok) {
        Write-Host ('[OK] ' + $Name + $suffix) -ForegroundColor Green
    } else {
        Write-Host ('[FAIL] ' + $Name + $suffix) -ForegroundColor Red
        $script:CoreFailures++
    }
}

function Restore-PendingTrustE2EEnvironment {
    param(
        $PrevLocalAppData,
        $PrevSkip,
        $PrevDry,
        $PrevRepo,
        [string]$IsolatedDir
    )
    if ($null -eq $PrevLocalAppData) {
        Remove-Item -Path env:LOCALAPPDATA -ErrorAction SilentlyContinue
    } else {
        $env:LOCALAPPDATA = $PrevLocalAppData
    }
    if ($null -eq $PrevSkip) {
        Remove-Item -Path env:HERMES_SKIP_PENDING_TRUST_ON_START -ErrorAction SilentlyContinue
    } else {
        $env:HERMES_SKIP_PENDING_TRUST_ON_START = $PrevSkip
    }
    if ($null -eq $PrevDry) {
        Remove-Item -Path env:HERMES_PENDING_TRUST_E2E_DRY_RUN -ErrorAction SilentlyContinue
    } else {
        $env:HERMES_PENDING_TRUST_E2E_DRY_RUN = $PrevDry
    }
    if ($null -eq $PrevRepo) {
        Remove-Item -Path env:HERMES_REPO_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:HERMES_REPO_ROOT = $PrevRepo
    }
    if (Test-Path -LiteralPath $IsolatedDir) {
        $parent = Split-Path -Parent $IsolatedDir
        if ($parent) {
            Remove-Item -LiteralPath $parent -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

function Invoke-PendingTrustStartE2ECore {
    param(
        [string]$RepoRoot,
        [string]$LauncherPath,
        [string]$IsolatedHermesDir = ''
    )

    Write-Host '--- PendingTrust core: module lifecycle ---' -ForegroundColor Cyan
    Clear-PendingTrustRuntime
    Set-PendingTrustRuntime -Source 'UPDATE_HERMES' -Reason 'E2E test' -RepoRoot $RepoRoot
    Add-PendingTrustE2EStep 'Set-PendingTrustRuntime' (Test-PendingTrustRuntime)

    $first = Get-PendingTrustRuntime
    Start-Sleep -Milliseconds 30
    Set-PendingTrustRuntime -Source 'UPDATE_HERMES' -Reason 'E2E refresh' -RepoRoot $RepoRoot
    $second = Get-PendingTrustRuntime
    Add-PendingTrustE2EStep 'created_at behouden' ($first.created_at -eq $second.created_at) $first.created_at

    $a1 = Register-PendingTrustRuntimeAttempt -RepoRoot $RepoRoot
    $a2 = Register-PendingTrustRuntimeAttempt -RepoRoot $RepoRoot
    $attemptOk = ($a1 -eq 1) -and ($a2 -eq 2)
    Add-PendingTrustE2EStep 'attempt counter' $attemptOk ('a1=' + $a1 + ' a2=' + $a2)

    Clear-PendingTrustRuntime
    Add-PendingTrustE2EStep 'Clear-PendingTrustRuntime' (-not (Test-PendingTrustRuntime))

    $stalePath = Get-PendingTrustRuntimePath
    @{ status = 'done'; attempts = 0 } | ConvertTo-Json -Compress | Set-Content -LiteralPath $stalePath -Encoding UTF8
    Add-PendingTrustE2EStep 'stale status niet pending' (-not (Test-PendingTrustRuntime))
    Clear-StalePendingTrustRuntimeFile
    Add-PendingTrustE2EStep 'Clear-StalePendingTrustRuntimeFile' (-not (Test-Path -LiteralPath $stalePath))

    Write-Host '--- PendingTrust core: identity repair ---' -ForegroundColor Cyan
    $identityRoot = Join-Path (Split-Path -Parent $IsolatedHermesDir) 'identity_mock_hermes'
    $idCoreMemDir = Join-Path $identityRoot 'profiles\core\memories'
    New-Item -ItemType Directory -Path $idCoreMemDir -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $identityRoot 'config.yaml') -Value 'model: test' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $identityRoot 'profiles\core\config.yaml') -Value @'
memory:
  memory_char_limit: 4000
  user_char_limit: 1800
'@ -Encoding UTF8
    $idMemPath = Join-Path $idCoreMemDir 'MEMORY.md'
    Set-Content -LiteralPath $idMemPath -Value @(
        'Runtime: C:\Users\jamel\AppData\Local\hermes',
        'Note from Jamel about strategy.'
    ) -Encoding UTF8
    . (Join-Path $RepoRoot 'windows/scripts/MemoryAuditCommon.ps1')
    $leaksPre = Get-MemoryFileIdentityLeakLines -FilePath $idMemPath
    Add-PendingTrustE2EStep 'identity mock has leak' ($leaksPre.Count -ge 1) ('count=' + $leaksPre.Count)
    $repairPre = Repair-HermesRuntimeIdentity -HermesRoot $identityRoot -Quiet
    Add-PendingTrustE2EStep 'identity repair changed file' ($repairPre.FilesChanged -ge 1)
    $leaksPost = Get-MemoryFileIdentityLeakLines -FilePath $idMemPath
    Add-PendingTrustE2EStep 'identity repair clears leak' ($leaksPost.Count -eq 0)

    Write-Host '--- PendingTrust core: launcher gedrag ---' -ForegroundColor Cyan

    & $LauncherPath -RepoRoot $RepoRoot -Quiet | Out-Null
    Add-PendingTrustE2EStep 'no pending exit 0' ($LASTEXITCODE -eq 0)

    Set-PendingTrustRuntime -Source 'UPDATE_HERMES' -Reason 'skip-flag E2E' -RepoRoot $RepoRoot
    $env:HERMES_SKIP_PENDING_TRUST_ON_START = '1'
    & $LauncherPath -RepoRoot $RepoRoot | Out-Null
    Add-PendingTrustE2EStep 'skip-flag exit 0' ($LASTEXITCODE -eq 0)
    Add-PendingTrustE2EStep 'skip-flag behoudt pending' (Test-PendingTrustRuntime)
    $skipAttempts = (Get-PendingTrustRuntime).attempts
    Add-PendingTrustE2EStep 'skip-flag no extra attempt' ($skipAttempts -eq 0)
    Remove-Item -Path env:HERMES_SKIP_PENDING_TRUST_ON_START -ErrorAction SilentlyContinue

    Clear-PendingTrustRuntime
    Set-PendingTrustRuntime -Source 'UPDATE_HERMES' -Reason 'max attempts E2E' -RepoRoot $RepoRoot
    Register-PendingTrustRuntimeAttempt -RepoRoot $RepoRoot | Out-Null
    Register-PendingTrustRuntimeAttempt -RepoRoot $RepoRoot | Out-Null
    Register-PendingTrustRuntimeAttempt -RepoRoot $RepoRoot | Out-Null
    $attemptsBeforeMax = (Get-PendingTrustRuntime).attempts
    & $LauncherPath -RepoRoot $RepoRoot | Out-Null
    $attemptsAfterMax = (Get-PendingTrustRuntime).attempts
    $maxOk = ($attemptsBeforeMax -eq $attemptsAfterMax) -and ($attemptsAfterMax -ge 3)
    Add-PendingTrustE2EStep 'max attempts exit 0' ($LASTEXITCODE -eq 0)
    Add-PendingTrustE2EStep 'max attempts drempel bereikt' (Test-PendingTrustRuntimeMaxAttemptsReached)
    Add-PendingTrustE2EStep 'max attempts no fourth run' $maxOk
    Add-PendingTrustE2EStep 'max attempts pending blijft' (Test-PendingTrustRuntime)

    Clear-PendingTrustRuntime
    Set-PendingTrustRuntime -Source 'UPDATE_HERMES' -Reason 'dry-run E2E' -RepoRoot $RepoRoot
    $env:HERMES_PENDING_TRUST_E2E_DRY_RUN = '1'
    $env:HERMES_REPO_ROOT = $RepoRoot
    & $LauncherPath -RepoRoot $RepoRoot | Out-Null
    Add-PendingTrustE2EStep 'dry-run exit 0' ($LASTEXITCODE -eq 0)
    Add-PendingTrustE2EStep 'dry-run cleared pending' (-not (Test-PendingTrustRuntime))
    Remove-Item -Path env:HERMES_PENDING_TRUST_E2E_DRY_RUN -ErrorAction SilentlyContinue
}

$modulePath = Join-Path $RepoRoot 'windows/scripts/TrustRuntimePending.psm1'
$launcherPath = Join-Path $RepoRoot 'windows/scripts/launch_pending_trust_runtime.ps1'
Import-Module $modulePath -Force

$prevLocalAppData = $env:LOCALAPPDATA
$prevSkip = $env:HERMES_SKIP_PENDING_TRUST_ON_START
$prevDry = $env:HERMES_PENDING_TRUST_E2E_DRY_RUN
$prevRepo = $env:HERMES_REPO_ROOT
$env:LOCALAPPDATA = Split-Path -Parent $IsolatedHermesDir
if (-not (Test-Path -LiteralPath $IsolatedHermesDir)) {
    New-Item -ItemType Directory -Path $IsolatedHermesDir -Force | Out-Null
}

Invoke-PendingTrustStartE2ECore -RepoRoot $RepoRoot -LauncherPath $launcherPath -IsolatedHermesDir $IsolatedHermesDir

Restore-PendingTrustE2EEnvironment -PrevLocalAppData $prevLocalAppData -PrevSkip $prevSkip -PrevDry $prevDry -PrevRepo $prevRepo -IsolatedDir $IsolatedHermesDir

exit $script:CoreFailures
