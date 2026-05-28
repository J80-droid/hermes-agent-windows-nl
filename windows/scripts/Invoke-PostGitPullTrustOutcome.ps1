#requires -Version 5.1
# Registreer pending trust na mislukte SYNC_TRUST_RUNTIME of wis stamp bij succes.
param(
    [Parameter(Mandatory)]
    [int]$TrustExitCode,
    [Parameter(Mandatory)]
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$winDir = Split-Path -Parent $scriptDir

. (Join-Path $winDir 'HermesShellCommon.ps1')
Import-Module (Join-Path $scriptDir 'TrustRuntimePending.psm1') -Force

try {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
} catch {
    Write-HermesFail ('Ongeldig RepoRoot: ' + $_.Exception.Message)
    exit 1
}

if ($TrustExitCode -ne 0) {
    Write-HermesWarn 'SYNC_TRUST_RUNTIME mislukt  - pending trust bij volgende start.'
    try {
        Register-PendingTrustRuntimeRequired -Source 'POST_GIT_PULL' -Reason 'Trust runtime mislukt tijdens POST_GIT_PULL' -RepoRoot $RepoRoot
    } catch {
        Write-HermesFail ('Kon pending_trust_runtime.json niet schrijven: ' + $_.Exception.Message)
        exit 1
    }
    exit $TrustExitCode
}

try {
    Clear-PendingTrustRuntime | Out-Null
} catch {
    Write-HermesWarn ('Kon pending trust-stamp niet wissen: ' + $_.Exception.Message)
}
Write-HermesOk 'Trust runtime gesynchroniseerd.'
exit 0
