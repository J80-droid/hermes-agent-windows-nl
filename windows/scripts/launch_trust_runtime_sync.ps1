# Stamp-gestuurde trust/memory sync bij start (licht; geen RUN_MEMORY_PRODUCTION_GATE).
# Equivalent van windows\SYNC_TRUST_RUNTIME.bat voor dagelijkse start — alleen bij drift of ontbrekende profielen.
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
        Write-Host '[INFO] Trust runtime sync overgeslagen (HERMES_SKIP_TRUST_RUNTIME_ON_START=1).' -ForegroundColor DarkGray
    }
    exit 0
}

if ($env:HERMES_FORCE_TRUST_SYNC -eq '1') {
    $Force = $true
}

if (-not $RepoRoot) {
    if ($env:HERMES_REPO_ROOT) {
        $RepoRoot = $env:HERMES_REPO_ROOT.Trim().Trim('"')
    } else {
        $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    }
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$needRun = Test-TrustRuntimeSyncNeeded -RepoRoot $RepoRoot -Force:$Force
if (-not $needRun) {
    if (-not $Quiet) {
        Write-Host '[INFO] Trust/memory up-to-date (stamp OK).' -ForegroundColor DarkGray
    }
    exit 0
}

if (-not $Quiet) {
    Write-Host '[INFO] Trust/memory sync (profielen, limits, geen productie-poort)...' -ForegroundColor Cyan
}

$light = Join-Path $PSScriptRoot 'Invoke-TrustRuntimeLight.ps1'
if (-not (Test-Path -LiteralPath $light)) {
    Write-Host '[FAIL] Invoke-TrustRuntimeLight.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}

& $light -RepoRoot $RepoRoot -SkipProductionGate -Quiet:$Quiet
if (Test-NativeCommandFailed -or ($null -ne $LASTEXITCODE -and [int]$LASTEXITCODE -ne 0)) {
    Write-Host '[WARN] Trust runtime sync mislukt — pending trust bij volgende start.' -ForegroundColor Yellow
    try {
        Register-PendingTrustRuntimeRequired -Source 'TRUST_RUNTIME_SYNC' -Reason 'Trust/memory sync mislukt bij start' -RepoRoot $RepoRoot
    } catch {
        Write-Host '[WARN] Kon pending_trust_runtime.json niet schrijven.' -ForegroundColor Yellow
    }
    exit 1
}

$hermesRoot = Get-TrustRuntimeHermesRoot
if (-not (Test-TrustRuntimeMemoryAuditClean -HermesRoot $hermesRoot)) {
    Write-Host '[WARN] Memory-audit niet schoon na sync — geen stamp, pending trust.' -ForegroundColor Yellow
    try {
        Register-PendingTrustRuntimeRequired -Source 'TRUST_RUNTIME_SYNC' -Reason 'Memory audit niet schoon na trust sync' -RepoRoot $RepoRoot
    } catch {
        Write-Host '[WARN] Kon pending_trust_runtime.json niet schrijven.' -ForegroundColor Yellow
    }
    exit 1
}

Set-TrustRuntimeSyncStamp
if (-not $Quiet) {
    Write-Host '[OK] Trust/memory sync voltooid.' -ForegroundColor Green
}
exit 0
