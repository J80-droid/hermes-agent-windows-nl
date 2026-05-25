<#

.SYNOPSIS

    Zet team-display in alle profiel-config(s) (idempotent YAML-patch).

.PARAMETER ActiveProfileOnly

    Alleen sticky active_profile (via hermes config set, legacy).

.NOTES

    Standaard: windows/scripts/apply_team_display_profiles.py (alle profiles\*).

#>

param(

    [switch]$ActiveProfileOnly,

    [string]$HermesRoot = ''

)



$ErrorActionPreference = 'Stop'

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
. (Join-Path $scriptDir 'HermesShellCommon.ps1')

$repoRoot = (Resolve-Path (Join-Path $scriptDir '..')).Path



function Get-HermesRootConfigDir {

    param([string]$Override = '')

    if ($Override) { return (Resolve-Path -LiteralPath $Override).Path }

    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'

    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }

    $homeRoot = Join-Path $env:USERPROFILE '.hermes'

    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }

    if (Test-Path -LiteralPath $localRoot) { return $localRoot }

    return $homeRoot

}



$condaExe = $null

foreach ($p in @(

        (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),

        (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe'),

        (Join-Path ${env:ProgramData} 'miniconda3\Scripts\conda.exe'),

        (Join-Path ${env:ProgramData} 'anaconda3\Scripts\conda.exe')

    )) {

    if ($p -and (Test-Path -LiteralPath $p)) { $condaExe = $p; break }

}

if (-not $condaExe) {

    Write-Host '[ERROR] conda.exe niet gevonden (miniconda3).' -ForegroundColor Red

    exit 1

}



$hermesRoot = Get-HermesRootConfigDir -Override $HermesRoot

Write-Host ('[INFO] ' + 'Hermes root: ' + $hermesRoot) -ForegroundColor Cyan

if ($ActiveProfileOnly) {
    $activeProfile = 'core'
    $activeProfilePath = Join-Path $hermesRoot 'active_profile'
    if (Test-Path -LiteralPath $activeProfilePath) {
        $activeProfile = (Get-Content -LiteralPath $activeProfilePath -Raw -Encoding UTF8).Trim()
    }
    $profileHome = Join-Path $hermesRoot ('profiles\' + $activeProfile)
    if (-not (Test-Path -LiteralPath $profileHome)) {
        New-Item -ItemType Directory -Path $profileHome -Force | Out-Null
    }
    . (Join-Path $scriptDir 'scripts\HermesHomeCommon.ps1')
    Ensure-UserHermesHomeRoot -FixUserEnv -Quiet | Out-Null
    Write-Host ('[INFO] ' + 'Profiel display patch: ' + $activeProfile + ' (HERMES_HOME blijft root)') -ForegroundColor Cyan
    & $condaExe run -n hermes-env --no-capture-output python (Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/scripts/apply_team_display_profiles.py') --profile $activeProfile
    if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
    Write-Host '[OK] Team display op actief profiel.' -ForegroundColor Green
    exit 0
}

$env:HERMES_ROOT = $hermesRoot

Write-Host '[INFO] Team display (alle profielen via YAML-patch)...' -ForegroundColor Cyan

& $condaExe run -n hermes-env --no-capture-output python (Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/scripts/apply_team_display_profiles.py')

if (Test-NativeCommandFailed) { exit $LASTEXITCODE }

Write-Host '[OK] Team display-defaults op alle profielen. Hermes opnieuw starten indien al open.' -ForegroundColor Green

exit 0
