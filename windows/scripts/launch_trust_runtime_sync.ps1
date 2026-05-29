# Stamp-gestuurde trust/memory sync bij start (licht; geen RUN_MEMORY_PRODUCTION_GATE).
param(
    [string]$RepoRoot = '',
    [switch]$Force,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'TrustRuntimeSync.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'TrustRuntimePending.psm1') -Force

if ($env:HERMES_SKIP_TRUST_RUNTIME_ON_START -eq '1') {
    if (-not $Quiet) {
        Write-HermesLaunchUi -Message 'Trust runtime sync overgeslagen (HERMES_SKIP_TRUST_RUNTIME_ON_START=1).' -Level Detail
    }
    exit 0
}

if ($env:HERMES_FORCE_TRUST_SYNC -eq '1') { $Force = $true }

if (-not $RepoRoot) {
    if ($env:HERMES_REPO_ROOT) { $RepoRoot = $env:HERMES_REPO_ROOT.Trim().Trim('"') }
    else { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$needRun = Test-TrustRuntimeSyncNeeded -RepoRoot $RepoRoot -Force:$Force
if (-not $needRun) {
    if (-not $Quiet) {
        Write-HermesLaunchUi -Message 'Trust/memory up-to-date (stamp OK).' -Level Detail
    }
    exit 0
}

Update-HermesLaunchActivity -Reason 'Profiel-geheugen synchroniseren...'
if (-not $Quiet) {
    Write-HermesLaunchUi -Message 'Trust/memory sync (profielen, limits, geen productie-poort)...' -Level Info
}

$light = Join-Path $PSScriptRoot 'Invoke-TrustRuntimeLight.ps1'
if (-not (Test-Path -LiteralPath $light)) {
    Write-HermesLaunchUi -Message 'Invoke-TrustRuntimeLight.ps1 ontbreekt' -Level Error -ForceConsole
    exit 1
}

if (Test-HermesLaunchConsoleCapture) {
    $trustCode = Invoke-HermesCapturedProcess -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $light, '-RepoRoot', $RepoRoot, '-SkipProductionGate', '-Quiet'
    ) -Quiet -FilterNoise
} else {
    & $light -RepoRoot $RepoRoot -SkipProductionGate -Quiet:$Quiet
    $trustCode = [int]$LASTEXITCODE
}

if ($trustCode -ne 0) {
    Write-HermesLaunchUi -Message 'Trust runtime sync mislukt — pending trust bij volgende start.' -Level Warn
    try {
        Register-PendingTrustRuntimeRequired -Source 'TRUST_RUNTIME_SYNC' -Reason 'Trust/memory sync mislukt bij start' -RepoRoot $RepoRoot
    } catch {
        Write-HermesLaunchUi -Message 'Kon pending_trust_runtime.json niet schrijven.' -Level Warn
    }
    exit 1
}

$hermesRoot = Get-TrustRuntimeHermesRoot
if (-not (Test-TrustRuntimeMemoryAuditClean -HermesRoot $hermesRoot)) {
    Write-HermesLaunchUi -Message 'Memory-audit niet schoon na sync — geen stamp, pending trust.' -Level Warn
    try {
        Register-PendingTrustRuntimeRequired -Source 'TRUST_RUNTIME_SYNC' -Reason 'Memory audit niet schoon na trust sync' -RepoRoot $RepoRoot
    } catch {
        Write-HermesLaunchUi -Message 'Kon pending_trust_runtime.json niet schrijven.' -Level Warn
    }
    exit 1
}

Set-TrustRuntimeSyncStamp
if (-not $Quiet) {
    Write-HermesLaunchUi -Message 'Trust/memory sync voltooid.' -Level Ok
}
exit 0
