# Start-hook: lichte trust-nazorg als pending_trust_runtime.json bestaat (na mislukte UPDATE).
# Env: HERMES_SKIP_PENDING_TRUST_ON_START=1 (overslaan); HERMES_PENDING_TRUST_E2E_DRY_RUN=1 (alleen E2E, geen memory-sync).

param(

    [string]$RepoRoot = '',

    [switch]$Quiet

)



$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot 'TrustRuntimePending.psm1') -Force



function Resolve-PendingTrustRepoRoot {

    param(

        [string]$Preferred,

        [string]$FallbackFromStamp = ''

    )

    $candidates = @()

    if ($Preferred) { $candidates += $Preferred.Trim().Trim('"') }

    if ($env:HERMES_REPO_ROOT) { $candidates += $env:HERMES_REPO_ROOT.Trim().Trim('"') }

    if ($FallbackFromStamp) { $candidates += $FallbackFromStamp.Trim().Trim('"') }

    $candidates += (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path



    foreach ($candidate in $candidates) {

        if (-not $candidate) { continue }

        if (-not (Test-Path -LiteralPath $candidate)) { continue }

        return (Resolve-Path -LiteralPath $candidate).Path

    }

    throw "Geen geldige RepoRoot gevonden (laatste poging: $($candidates[-1]))"

}



if ($env:HERMES_SKIP_PENDING_TRUST_ON_START -eq '1') {

    if (-not $Quiet) {

        Write-Host '[INFO] Pending trust overgeslagen (HERMES_SKIP_PENDING_TRUST_ON_START=1).' -ForegroundColor DarkGray

    }

    exit 0

}



Clear-StalePendingTrustRuntimeFile



if (-not (Test-PendingTrustRuntime)) {

    exit 0

}



$data = Get-PendingTrustRuntime

if (-not $data) {

    exit 0

}



if (Test-PendingTrustRuntimeMaxAttemptsReached) {

    Write-PendingTrustRuntimeFallbackHint

    exit 0

}



try {

    $RepoRoot = Resolve-PendingTrustRepoRoot -Preferred $RepoRoot -FallbackFromStamp $data.repo_root

} catch {

    Write-Host ('[FAIL] ' + $_.Exception.Message) -ForegroundColor Red

    Write-PendingTrustRuntimeFallbackHint

    exit 1

}



$attempt = Register-PendingTrustRuntimeAttempt -RepoRoot $RepoRoot

if (-not $Quiet) {

    Write-Host ''

    Write-Host '[INFO] Na update: geheugen en trust even afronden (~1 min)...' -ForegroundColor Cyan

    if ($data.reason) {

        Write-Host "  Reden: $($data.reason)" -ForegroundColor DarkGray

    }

    if ($attempt -gt 1) {

        Write-Host "  Poging $attempt van 3" -ForegroundColor DarkGray

    }

}



$lightPs1 = Join-Path $PSScriptRoot 'Invoke-TrustRuntimeLight.ps1'

if (-not (Test-Path -LiteralPath $lightPs1)) {

    Write-Host '[FAIL] Invoke-TrustRuntimeLight.ps1 ontbreekt' -ForegroundColor Red

    exit 1

}

if ($env:HERMES_PENDING_TRUST_E2E_DRY_RUN -eq '1') {
    if (-not $Quiet) {
        Write-Host '[INFO] E2E dry-run: trust-nazorg overgeslagen (geen memory-sync).' -ForegroundColor DarkGray
    }
    Clear-PendingTrustRuntime
    exit 0
}

& $lightPs1 -RepoRoot $RepoRoot -SkipProductionGate -Quiet:$Quiet

$rc = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }

if ($rc -ne 0) {

    if (Test-PendingTrustRuntimeMaxAttemptsReached) {

        Write-PendingTrustRuntimeFallbackHint

    } else {

        Write-Host '[WARN] Trust-nazorg mislukt - wordt opnieuw geprobeerd bij volgende start.' -ForegroundColor Yellow

        Write-Host '  Kopieer: set HERMES_SKIP_MEMORY_PRODUCTION_GATE=1 && windows\SYNC_TRUST_RUNTIME.bat' -ForegroundColor DarkYellow

    }

    exit 0

}



exit 0

