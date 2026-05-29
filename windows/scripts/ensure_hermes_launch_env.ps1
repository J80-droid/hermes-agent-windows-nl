<#
.SYNOPSIS
    Zet HERMES_HOME op runtime root en run verify_hermes_home vóór Hermes start.
#>
param(
    [switch]$FixUserEnv,
    [switch]$StrictDrift,
    [switch]$SkipVerify
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
. (Join-Path $scriptDir 'HermesHomeCommon.ps1')
. (Join-Path (Split-Path -Parent $scriptDir) 'HermesShellCommon.ps1')

$root = Initialize-UserHermesHomeRoot -FixUserEnv:$FixUserEnv
$homeLine = '[INFO] HERMES_HOME=' + $root
if ($global:HermesLaunchVisualState -and $global:HermesLaunchVisualState.SpinnerActive) {
    Add-HermesLaunchLogLine -Message $homeLine
} elseif ((Get-Command Test-HermesLaunchConsoleCapture -ErrorAction SilentlyContinue) -and (Test-HermesLaunchConsoleCapture)) {
    Add-HermesLaunchLogLine -Message $homeLine
} else {
    Write-Host $homeLine -ForegroundColor Cyan
}

if (-not $SkipVerify) {
    $verify = Join-Path $scriptDir 'verify_hermes_home.ps1'
    if (Test-Path -LiteralPath $verify) {
        & $verify -StrictDrift:$StrictDrift
        if ($LASTEXITCODE -ne 0) {
            Write-Host '[FAIL] verify_hermes_home - start afgebroken' -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }
}
exit 0
