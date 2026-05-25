<#
.SYNOPSIS
    Herstart Hermes gateway na HERMES_HOME-fix zodat gateway.cmd aligned blijft.
.PARAMETER SkipRestart
    Alleen verify, geen hermes gateway restart.
#>
param(
    [switch]$SkipRestart,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
. (Join-Path $scriptDir 'HermesHomeCommon.ps1')

Initialize-UserHermesHomeRoot -FixUserEnv -Quiet | Out-Null

if (Test-HermesGatewayHomeAlignment -Quiet:$Quiet) {
    if (-not $Quiet) {
        Write-Host '[OK] Gateway HERMES_HOME aligned' -ForegroundColor Green
    }
    exit 0
}

if (-not $Quiet) {
    Write-Host '[WARN] Gateway HERMES_HOME mismatch — herstart gateway...' -ForegroundColor Yellow
}

if ($SkipRestart) {
    exit 1
}

$conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
if (-not (Test-Path -LiteralPath $conda)) {
    Write-Host '[FAIL] conda niet gevonden — run handmatig: hermes gateway restart' -ForegroundColor Red
    exit 1
}

& $conda run -n hermes-env --no-capture-output hermes gateway restart
if ($LASTEXITCODE -ne 0) {
    Write-Host '[WARN] gateway restart faalde — probeer: hermes gateway install' -ForegroundColor Yellow
    exit $LASTEXITCODE
}

if (Test-HermesGatewayHomeAlignment -Quiet) {
    Write-Host '[OK] Gateway herstart + HERMES_HOME aligned' -ForegroundColor Green
    exit 0
}

Write-Host '[WARN] Gateway herstart OK maar HERMES_HOME nog misaligned — hermes gateway install' -ForegroundColor Yellow
exit 1
