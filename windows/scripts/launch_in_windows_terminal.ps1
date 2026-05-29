#requires -Version 5.1
param(
    [Parameter(Mandatory)][string]$RepoRoot,
    [string]$ExtraArgs = ''
)
$ErrorActionPreference = 'Stop'
$common = Join-Path $RepoRoot 'windows\HermesShellCommon.ps1'
if (-not (Test-Path -LiteralPath $common)) {
    Write-Error "Ontbrekend: $common"
    exit 1
}
. $common
Invoke-HermesLaunchInWindowsTerminal -RepoRoot $RepoRoot -ExtraArgs $ExtraArgs
exit 0
