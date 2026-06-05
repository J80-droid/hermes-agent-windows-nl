# Start-hook: lichte trust-nazorg als pending_trust_runtime.json bestaat (na mislukte UPDATE).
# Env: HERMES_SKIP_PENDING_TRUST_ON_START=1 (overslaan); HERMES_PENDING_TRUST_E2E_DRY_RUN=1 (alleen E2E, geen memory-sync).

param(

    [string]$RepoRoot = '',

    [switch]$Quiet

)



$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
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

        Write-HermesLaunchUi -Message 'Pending trust overgeslagen (HERMES_SKIP_PENDING_TRUST_ON_START=1).' -Level Detail

    }

    exit 0

}



Clear-StalePendingTrustRuntimeFile | Out-Null



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

    Write-HermesLaunchUi -Message $_.Exception.Message -Level Error -ForceConsole

    Write-PendingTrustRuntimeFallbackHint

    exit 1

}



$attempt = Register-PendingTrustRuntimeAttempt -RepoRoot $RepoRoot

if (-not $Quiet) {

    Update-HermesLaunchActivity -Reason 'Pending trust afronden (~1 min)...'
    Write-HermesLaunchUi -Message 'Na update: geheugen en trust even afronden (~1 min)...' -Level Info
    if ($data.reason) {
        Write-HermesLaunchUi -Message ('  Reden: ' + $data.reason) -Level Detail
    }
    if ($attempt -gt 1) {
        Write-HermesLaunchUi -Message ('  Poging ' + $attempt + ' van 3') -Level Detail
    }

}



$lightPs1 = Join-Path $PSScriptRoot 'Invoke-TrustRuntimeLight.ps1'

if (-not (Test-Path -LiteralPath $lightPs1)) {

    Write-HermesLaunchUi -Message 'Invoke-TrustRuntimeLight.ps1 ontbreekt' -Level Error -ForceConsole

    exit 1

}

if ($env:HERMES_PENDING_TRUST_E2E_DRY_RUN -eq '1') {
    if (-not $Quiet) {
        Write-HermesLaunchUi -Message 'E2E dry-run: trust-nazorg overgeslagen (geen memory-sync).' -Level Detail
    }
    Clear-PendingTrustRuntime
    exit 0
}

if (Test-HermesLaunchConsoleCapture) {
    $rc = Invoke-HermesCapturedProcess -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $lightPs1, '-RepoRoot', $RepoRoot, '-SkipProductionGate', '-Quiet'
    ) -Quiet -FilterNoise
} else {
    & $lightPs1 -RepoRoot $RepoRoot -SkipProductionGate -Quiet:$Quiet
    $rc = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
}

if ($rc -ne 0) {

    if (Test-PendingTrustRuntimeMaxAttemptsReached) {

        Write-PendingTrustRuntimeFallbackHint

    } else {

        Write-HermesLaunchUi -Message 'Trust-nazorg mislukt - wordt opnieuw geprobeerd bij volgende start.' -Level Warn -ForceConsole
        Write-HermesLaunchUi -Message '  Handmatig: windows/APPLY_TRUST_PROTOCOL.bat (na backup)' -Level Detail
        Write-HermesLaunchUi -Message '  Of: windows/scripts/repair_runtime_identity.ps1 && windows/SYNC_TRUST_RUNTIME.bat' -Level Detail

    }

    exit 0

}



exit 0

