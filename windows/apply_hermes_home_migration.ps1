<#
.SYNOPSIS
    Eénmalige split-home migratie: backup → deprecate → providers → preset → env → E2E.
#>
param(
    [switch]$SkipBackup,
    [switch]$SkipDeprecate,
    [switch]$SkipProviders,
    [switch]$SkipAuxiliary,
    [switch]$SkipEnvSync,
    [switch]$SkipE2E,
    [switch]$NoCopyAuxiliaryOnly,
    [switch]$NoPause
)

. (Join-Path $PSScriptRoot 'HermesShellCommon.ps1')

$ErrorActionPreference = 'Stop'
$useCopyAuxiliaryOnly = [bool]$NoCopyAuxiliaryOnly
$windowsRoot = if ($PSScriptRoot) { (Resolve-Path $PSScriptRoot).Path } else {
    Split-Path -Parent $MyInvocation.MyCommand.Path
}
$repoRoot = (Resolve-Path (Join-Path $windowsRoot '..')).Path
Set-Location $repoRoot

Write-Host '=== Hermes split-home migratie (automatisch) ===' -ForegroundColor Cyan
Write-HermesInfo ('Repo: ' + $repoRoot)
Write-HermesInfo 'Keten: backup -> deprecate -> providers -> preset -> strip -> env -> E2E'
Write-Host ''

function Invoke-Step {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][scriptblock]$Action
    )
    Write-Host ('--- ' + $Name + ' ---') -ForegroundColor Cyan
    & $Action
    if (Test-NativeCommandFailed) {
        Write-HermesFail ('Stap mislukt: ' + $Name)
        exit $LASTEXITCODE
    }
    Write-HermesOk $Name
    Write-Host ''
}

$step = 1
$total = 7

if (-not $SkipBackup) {
    Invoke-Step -Name (Format-HermesStepLabel -Step $step -Total $total -Suffix 'Backup (MANAGE_BACKUPS)') -Action {
        $env:HERMES_BACKUP_NONINTERACTIVE = '1'
        & (Join-Path $windowsRoot 'backup_hermes.ps1') -SkipPause
    }
} else {
    Write-HermesSkip (Format-HermesStepLabel -Step $step -Total $total -Suffix 'Backup (-SkipBackup)')
    Write-Host ''
}
$step++

if (-not $SkipDeprecate) {
    Invoke-Step -Name (Format-HermesStepLabel -Step $step -Total $total -Suffix 'Deprecate legacy config') -Action {
        if (-not $useCopyAuxiliaryOnly) {
            & (Join-Path $windowsRoot 'scripts\deprecate_legacy_config.ps1') -CopyAuxiliaryOnly
        } else {
            & (Join-Path $windowsRoot 'scripts\deprecate_legacy_config.ps1')
        }
    }
} else {
    Write-HermesSkip (Format-HermesStepLabel -Step $step -Total $total -Suffix 'Deprecate (-SkipDeprecate)')
    Write-Host ''
}
$step++

if (-not $SkipAuxiliary) {
    Invoke-Step -Name (Format-HermesStepLabel -Step $step -Total $total -Suffix 'Auxiliary hybrid preset + strip profiles') -Action {
        & (Join-Path $windowsRoot 'scripts\apply_auxiliary_hybrid_preset.ps1')
    }
} else {
    Write-HermesSkip (Format-HermesStepLabel -Step $step -Total $total -Suffix 'Auxiliary (-SkipAuxiliary)')
    Write-Host ''
}
$step++

if (-not $SkipProviders) {
    Invoke-Step -Name (Format-HermesStepLabel -Step $step -Total $total -Suffix 'Merge legacy providers (Venice)') -Action {
        $conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
        & $conda run -n hermes-env --no-capture-output python (Join-Path $windowsRoot 'scripts\merge_legacy_providers_config.py')
    }
} else {
    Write-HermesSkip (Format-HermesStepLabel -Step $step -Total $total -Suffix 'Providers (-SkipProviders)')
    Write-Host ''
}
$step++

Invoke-Step -Name (Format-HermesStepLabel -Step $step -Total $total -Suffix 'Strip profile global blocks') -Action {
    $conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
    & $conda run -n hermes-env --no-capture-output python (Join-Path $windowsRoot 'scripts\strip_profile_global_config_blocks.py')
}
$step++

if (-not $SkipEnvSync) {
    Invoke-Step -Name (Format-HermesStepLabel -Step $step -Total $total -Suffix 'Sync API env (legacy -> runtime)') -Action {
        $env:HERMES_SKIP_PAUSE = '1'
        & (Join-Path $windowsRoot 'sync_hermes_api_env.ps1')
    }
} else {
    Write-HermesSkip (Format-HermesStepLabel -Step $step -Total $total -Suffix 'Env sync (-SkipEnvSync)')
    Write-Host ''
}
$step++

if (-not $SkipE2E) {
    Invoke-Step -Name (Format-HermesStepLabel -Step $step -Total $total -Suffix 'HermesHome E2E') -Action {
        & (Join-Path $windowsRoot 'audits\RUN_HERMES_HOME_E2E.ps1') -RepoRoot $repoRoot
    }
} else {
    Write-HermesSkip (Format-HermesStepLabel -Step $step -Total $total -Suffix 'E2E (-SkipE2E)')
    Write-Host ''
}

Write-Host '=== HERMES SPLIT-HOME MIGRATIE: KLAAR ===' -ForegroundColor Green
Write-Host 'Start Hermes opnieuw: windows\launch_hermes.bat en /new in TUI.' -ForegroundColor Cyan
if (-not $NoPause -and -not ($env:HERMES_SKIP_PAUSE -in @('1', 'true', 'True'))) {
    Read-Host 'Druk Enter om af te sluiten'
}
exit 0
