<#
.SYNOPSIS
    Controleert gateway-service *.cmd HERMES_HOME alignment met runtime root.
.EXIT
    0 = OK, 1 = mismatch
#>
param(
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
. (Join-Path $scriptDir 'HermesHomeCommon.ps1')

if (Test-HermesGatewayHomeAlignment -Quiet:$Quiet) {
    exit 0
}
Write-Host '[FAIL] Gateway HERMES_HOME niet aligned — run REPAIR_GATEWAY_HOME.bat of: hermes gateway restart' -ForegroundColor Red
exit 1
