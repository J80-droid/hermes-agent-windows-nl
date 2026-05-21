#requires -Version 5.1
<#
.SYNOPSIS
  Doorverwijzing naar canoniek setup-script (scripts/windows/setup_hermes_windows.ps1).
.DESCRIPTION
  Bewerk alleen scripts/windows/setup_hermes_windows.ps1.
  launch_hermes.bat roept dit wrapper-bestand aan; geen volledige kopie meer (voorkomt IDE false positives).
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$RepoRoot = '',
    [switch]$NoShortcut,
    [switch]$NoTaskbarLinks,
    [switch]$ForceLogoBat,
    [switch]$ForceLaunchBat,
    [switch]$FullSetup
)

$ErrorActionPreference = 'Stop'
$canon = Join-Path $PSScriptRoot (Join-Path '..' (Join-Path 'scripts' (Join-Path 'windows' 'setup_hermes_windows.ps1')))
if (-not (Test-Path -LiteralPath $canon)) {
    throw "Canoniek setup ontbreekt: $canon"
}
& $canon @PSBoundParameters
