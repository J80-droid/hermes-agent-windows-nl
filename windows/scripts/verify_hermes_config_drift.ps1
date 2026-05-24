<#
.SYNOPSIS
    Controleert split-home config drift (~/.hermes vs LOCALAPPDATA runtime).
.EXIT
    0 = OK, 1 = drift of runtime ontbreekt
#>
param(
    [switch]$Strict,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
. (Join-Path $scriptDir 'HermesHomeCommon.ps1')

$ok = Test-HermesConfigDrift -Strict:$Strict -Quiet:$Quiet
if (-not $ok) { exit 1 }
exit 0
