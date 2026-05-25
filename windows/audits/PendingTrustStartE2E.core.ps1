# Geïsoleerde E2E-stappen voor pending trust-runtime bij start (temp LOCALAPPDATA).
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
    if ($Ok) {
        Write-Host ('[OK] ' + $Name + $(if ($Detail) { ' - ' + $Detail } else { '' })) -ForegroundColor Green
    } else {
        Write-Host ('[FAIL] ' + $Name + $(if ($Detail) { ' - ' + $Detail } else { '' })) -ForegroundColor Red
        $script:CoreFailures++
    }
}

$modulePath = Join-Path $RepoRoot 'windows/scripts/TrustRuntimePending.psm1'
$launcherPath = Join-Path $RepoRoot 'windows/scripts/launch_pending_trust_runtime.ps1'
Import-Module $modulePath -Force

$prevLocalAppData = $env:LOCALAPPDATA
$env:LOCALAPPDATA = Split-Path -Parent $IsolatedHermesDir
if (-not (Test-Path -LiteralPath $IsolatedHermesDir)) {
    New-Item -ItemType Directory -Path $IsolatedHermesDir -Force | Out-Null
}

try {
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
    Add-PendingTrustE2EStep 'attempt counter' ($a1 -eq 1 -and $a2 -eq 2) "a1=$a1 a2=$a2"

    Clear-PendingTrustRuntime
    Add-PendingTrustE2EStep 'Clear-PendingTrustRuntime' (-not (Test-PendingTrustRuntime))

    $stalePath = Get-PendingTrustRuntimePath
    @{ status = 'done'; attempts = 0 } | ConvertTo-Json -Compress | Set-Content -LiteralPath $stalePath -Encoding UTF8
    Add-PendingTrustE2EStep 'stale status niet pending' (-not (Test-PendingTrustRuntime))
    Clear-StalePendingTrustRuntimeFile
    Add-PendingTrustE2EStep 'Clear-StalePendingTrustRuntimeFile' (-not (Test-Path -LiteralPath $stalePath))

    Write-Host '--- PendingTrust core: launcher gedrag ---' -ForegroundColor Cyan

    $prevSkip = $env:HERMES_SKIP_PENDING_TRUST_ON_START
    $prevDry = $env:HERMES_PENDING_TRUST_E2E_DRY_RUN
    $prevRepo = $env:HERMES_REPO_ROOT

    $noPendingOut = & $launcherPath -RepoRoot $RepoRoot -Quiet 2>&1 | Out-String
    Add-PendingTrustE2EStep 'geen pending: exit 0' ($LASTEXITCODE -eq 0)
    Add-PendingTrustE2EStep 'geen pending: geen nazorg-tekst' ($noPendingOut -notmatch 'Na update')

    Set-PendingTrustRuntime -Source 'UPDATE_HERMES' -Reason 'skip-flag E2E' -RepoRoot $RepoRoot
    $env:HERMES_SKIP_PENDING_TRUST_ON_START = '1'
    $skipOut = & $launcherPath -RepoRoot $RepoRoot 2>&1 | Out-String
    Add-PendingTrustE2EStep 'skip-flag exit 0' ($LASTEXITCODE -eq 0)
    Add-PendingTrustE2EStep 'skip-flag behoudt pending' (Test-PendingTrustRuntime)
    Add-PendingTrustE2EStep 'skip-flag melding' ($skipOut -match 'overgeslagen')
    Remove-Item Env:\HERMES_SKIP_PENDING_TRUST_ON_START -ErrorAction SilentlyContinue

    Clear-PendingTrustRuntime
    Set-PendingTrustRuntime -Source 'UPDATE_HERMES' -Reason 'max attempts E2E' -RepoRoot $RepoRoot
    Register-PendingTrustRuntimeAttempt -RepoRoot $RepoRoot | Out-Null
    Register-PendingTrustRuntimeAttempt -RepoRoot $RepoRoot | Out-Null
    Register-PendingTrustRuntimeAttempt -RepoRoot $RepoRoot | Out-Null
    $maxOut = & $launcherPath -RepoRoot $RepoRoot 2>&1 | Out-String
    Add-PendingTrustE2EStep 'max attempts exit 0' ($LASTEXITCODE -eq 0)
    Add-PendingTrustE2EStep 'max attempts fallback hint' ($maxOut -match 'meerdere pogingen')
    Add-PendingTrustE2EStep 'max attempts geen lichte keten' ($maxOut -notmatch 'Trust-nazorg: geheugen')
    Add-PendingTrustE2EStep 'max attempts pending blijft' (Test-PendingTrustRuntime)

    Clear-PendingTrustRuntime
    Set-PendingTrustRuntime -Source 'UPDATE_HERMES' -Reason 'dry-run E2E' -RepoRoot $RepoRoot
    $env:HERMES_PENDING_TRUST_E2E_DRY_RUN = '1'
    $env:HERMES_REPO_ROOT = $RepoRoot
    $dryOut = & $launcherPath -RepoRoot $RepoRoot 2>&1 | Out-String
    Add-PendingTrustE2EStep 'dry-run exit 0' ($LASTEXITCODE -eq 0)
    Add-PendingTrustE2EStep 'dry-run cleared pending' (-not (Test-PendingTrustRuntime))
    Add-PendingTrustE2EStep 'dry-run startmelding' ($dryOut -match 'Na update')
    Remove-Item Env:\HERMES_PENDING_TRUST_E2E_DRY_RUN -ErrorAction SilentlyContinue

} finally {
    if ($null -eq $prevLocalAppData) {
        Remove-Item Env:\LOCALAPPDATA -ErrorAction SilentlyContinue
    } else {
        $env:LOCALAPPDATA = $prevLocalAppData
    }
    if ($null -eq $prevSkip) {
        Remove-Item Env:\HERMES_SKIP_PENDING_TRUST_ON_START -ErrorAction SilentlyContinue
    } else {
        $env:HERMES_SKIP_PENDING_TRUST_ON_START = $prevSkip
    }
    if ($null -eq $prevDry) {
        Remove-Item Env:\HERMES_PENDING_TRUST_E2E_DRY_RUN -ErrorAction SilentlyContinue
    } else {
        $env:HERMES_PENDING_TRUST_E2E_DRY_RUN = $prevDry
    }
    if ($null -eq $prevRepo) {
        Remove-Item Env:\HERMES_REPO_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:HERMES_REPO_ROOT = $prevRepo
    }
    if (Test-Path -LiteralPath $IsolatedHermesDir) {
        Remove-Item -LiteralPath (Split-Path -Parent $IsolatedHermesDir) -Recurse -Force -ErrorAction SilentlyContinue
    }
}

exit $script:CoreFailures
