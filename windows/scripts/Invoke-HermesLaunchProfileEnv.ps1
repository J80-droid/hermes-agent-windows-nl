#requires -Version 5.1
<#
.SYNOPSIS
  Schrijft %TEMP%\hermes_launch_profile.cmd met env voor het gekozen launch-profiel.
.DESCRIPTION
  Wordt aangeroepen vanuit start_hermes.bat vóór launch_hermes.bat.
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = '',
    [string]$Profile = '',
    [string]$OutCmdPath = '',
    [switch]$ForceProfile,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$winDir = Split-Path -Parent $PSScriptRoot
. (Join-Path $winDir 'launch_profiles.ps1')
. (Join-Path $winDir 'scripts\HermesHomeCommon.ps1')

if (-not $RepoRoot.Trim()) {
    $RepoRoot = (Resolve-Path (Join-Path $winDir '..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}

if (-not $OutCmdPath.Trim()) {
    $OutCmdPath = Join-Path $env:TEMP 'hermes_launch_profile.cmd'
}

$configPath = ''
try { $configPath = Get-HermesCanonicalConfigPath } catch { $configPath = '' }

$resolved = Resolve-HermesLaunchProfile -Profile $Profile -ConfigPath $configPath -ForceProfile:$ForceProfile
Write-HermesLaunchProfileCmdFile -OutCmdPath $OutCmdPath -Profile $resolved -ForceProfile:$ForceProfile
if (-not $Quiet) { Write-Output $resolved }
