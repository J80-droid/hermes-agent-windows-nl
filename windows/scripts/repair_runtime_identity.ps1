# Pre-trust runtime identity scrub (line-by-line, zelfde allowlist als audit_profile_memories).
# Aangeroepen door Invoke-MemoryTrustPostSync, SYNC_TRUST_PROTOCOL (pre-sync) en handmatig. Idempotent.
# Opt-out: HERMES_SKIP_RUNTIME_IDENTITY_SCRUB=1
param(
    [string]$HermesRoot = '',
    [switch]$DryRun,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'MemoryAuditCommon.ps1')

if ($env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB -in @('1', 'true', 'True', 'yes', 'Yes')) {
    if (-not $Quiet) {
        Write-HermesInfo 'Runtime identity scrub overgeslagen (HERMES_SKIP_RUNTIME_IDENTITY_SCRUB).'
    }
    exit 0
}

$result = Repair-HermesRuntimeIdentity -HermesRoot $HermesRoot -DryRun:$DryRun -Quiet:$Quiet
if (-not $Quiet) {
    Write-HermesInfo ('Runtime scrub: ' + $result.FilesChanged + ' bestand(en), ' + $result.HitCount + ' regel(s)')
}
exit 0
