#requires -Version 5.1
param([Parameter(Mandatory)][string]$RepoRoot)
$ErrorActionPreference = 'SilentlyContinue'
$common = Join-Path $RepoRoot 'windows\HermesShellCommon.ps1'
if (-not (Test-Path -LiteralPath $common)) { exit 0 }
. $common
Invoke-HermesPrepareConsoleForChat -RepoRoot $RepoRoot
exit 0
