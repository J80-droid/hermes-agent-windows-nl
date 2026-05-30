#requires -Version 5.1
<#
.SYNOPSIS
  Legal proactive sparring E2E (parallelle invalshoeken, config repair, legal USER seed).

.DESCRIPTION
  Eén entrypoint voor RUN_LEGAL_PROACTIVE_SPARRING_E2E.bat, soul deploy, trust sync en RUN_AUDITS.

.PARAMETER Context
  SoulDeploy = na APPLY_SOUL_ANATOMY_RUNTIME of launch_soul_anatomy_deploy (deploy uitgevoerd).
  TrustSync  = na SYNC_TRUST_RUNTIME (respecteert HERMES_LEGAL_PROACTIVE_E2E_ON_TRUST).
  Manual     = expliciete aanroep (geen trust-default skip).

.EXIT
  0 = OK of overgeslagen via env
  1 = harness/core/Pester mislukt
#>
param(
    [string]$RepoRoot = '',
    [ValidateSet('SoulDeploy', 'TrustSync', 'Manual')]
    [string]$Context = 'Manual',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')
. (Join-Path $PSScriptRoot '..\HermesNativeInvoke.ps1')

if ($env:HERMES_SKIP_LEGAL_PROACTIVE_E2E -eq '1') {
    if (-not $Quiet) {
        Write-HermesInfo 'Legal proactive sparring E2E overgeslagen (HERMES_SKIP_LEGAL_PROACTIVE_E2E=1).'
    }
    exit 0
}

if ($Context -eq 'TrustSync' -and $env:HERMES_LEGAL_PROACTIVE_E2E_ON_TRUST -eq '0') {
    if (-not $Quiet) {
        Write-HermesInfo 'Legal proactive sparring E2E overgeslagen op trust-sync (HERMES_LEGAL_PROACTIVE_E2E_ON_TRUST=0).'
    }
    exit 0
}

try {
    if (-not $RepoRoot) {
        if ($env:HERMES_REPO_ROOT) { $RepoRoot = $env:HERMES_REPO_ROOT.Trim().Trim('"') }
        else { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
    } else {
        $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
    }
} catch {
    Write-HermesFail ('RepoRoot ongeldig of ontbreekt: ' + $RepoRoot + ' - ' + $_.Exception.Message)
    exit 1
}

$harness = Join-Path $RepoRoot 'audits\LegalProactiveSparringE2E.harness.py'
if (-not (Test-Path -LiteralPath $harness)) {
    Write-HermesFail "Legal proactive E2E harness ontbreekt: $harness"
    exit 1
}

$py = Resolve-HermesPythonExe -RepoRoot $RepoRoot
if (-not $py) {
    Write-HermesFail 'Geen Python (conda hermes-env of HERMES_PYTHON).'
    exit 1
}

if (-not $Quiet) {
    $ctxLabel = switch ($Context) {
        'SoulDeploy' { 'na SOUL deploy' }
        'TrustSync' { 'na trust sync' }
        default { 'handmatig' }
    }
    Write-HermesInfo "Legal proactive sparring E2E ($ctxLabel)..."
}

$prevRepo = $env:HERMES_REPO_ROOT
$env:HERMES_REPO_ROOT = $RepoRoot
try {
    $rc = Invoke-HermesNativeCommand -FilePath $py -ArgumentList @($harness) -WorkingDirectory $RepoRoot -Quiet:$Quiet
} finally {
    if ($null -eq $prevRepo) {
        Remove-Item Env:\HERMES_REPO_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:HERMES_REPO_ROOT = $prevRepo
    }
}

if ($rc -ne 0) {
    Write-HermesFail "Legal proactive sparring E2E mislukt (exit $rc)."
    exit $rc
}

if (-not $Quiet) {
    Write-HermesOk 'Legal proactive sparring E2E: ALL PASS'
}
exit 0
