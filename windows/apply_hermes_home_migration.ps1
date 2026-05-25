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
$windowsRoot = if ($PSScriptRoot) { (Resolve-Path $PSScriptRoot).Path } else {
    Split-Path -Parent $MyInvocation.MyCommand.Path
}
$repoRoot = (Resolve-Path (Join-Path $windowsRoot '..')).Path
Set-Location $repoRoot

Write-Host '=== Hermes split-home migratie (automatisch) ===' -ForegroundColor Cyan
Write-Host "[INFO] Repo: $repoRoot" -ForegroundColor Cyan
Write-Host '[INFO] Keten: backup -> deprecate -> providers -> preset -> strip -> env -> E2E' -ForegroundColor Cyan
Write-Host ''

function Invoke-Step {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][scriptblock]$Action
    )
    Write-Host "--- $Name ---" -ForegroundColor Cyan
    & $Action
    if (Test-NativeCommandFailed) {
        Write-Host "[FAIL] Stap mislukt: $Name" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "[OK] $Name" -ForegroundColor Green
    Write-Host ''
}

$step = 1
$total = 7

if (-not $SkipBackup) {
    Invoke-Step -Name "$step/$total Backup (MANAGE_BACKUPS)" -Action {
        $env:HERMES_BACKUP_NONINTERACTIVE = '1'
        & (Join-Path $windowsRoot 'backup_hermes.ps1') -SkipPause
    }
} else {
    Write-Host "[SKIP] $step/$total Backup (-SkipBackup)" -ForegroundColor Yellow
    Write-Host ''
}
$step++

if (-not $SkipDeprecate) {
    Invoke-Step -Name "$step/$total Deprecate legacy config" -Action {
        if (-not $NoCopyAuxiliaryOnly) {
            & (Join-Path $windowsRoot 'scripts\deprecate_legacy_config.ps1') -CopyAuxiliaryOnly
        } else {
            & (Join-Path $windowsRoot 'scripts\deprecate_legacy_config.ps1')
        }
    }
} else {
    Write-Host "[SKIP] $step/$total Deprecate (-SkipDeprecate)" -ForegroundColor Yellow
    Write-Host ''
}
$step++

if (-not $SkipAuxiliary) {
    Invoke-Step -Name "$step/$total Auxiliary hybrid preset + strip profiles" -Action {
        & (Join-Path $windowsRoot 'scripts\apply_auxiliary_hybrid_preset.ps1')
    }
} else {
    Write-Host "[SKIP] $step/$total Auxiliary (-SkipAuxiliary)" -ForegroundColor Yellow
    Write-Host ''
}
$step++

if (-not $SkipProviders) {
    Invoke-Step -Name "$step/$total Merge legacy providers (Venice)" -Action {
        $conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
        & $conda run -n hermes-env --no-capture-output python (Join-Path $windowsRoot 'scripts\merge_legacy_providers_config.py')
    }
} else {
    Write-Host "[SKIP] $step/$total Providers (-SkipProviders)" -ForegroundColor Yellow
    Write-Host ''
}
$step++

Invoke-Step -Name "$step/$total Strip profile global blocks" -Action {
    $conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
    & $conda run -n hermes-env --no-capture-output python (Join-Path $windowsRoot 'scripts\strip_profile_global_config_blocks.py')
}
$step++

if (-not $SkipEnvSync) {
    Invoke-Step -Name "$step/$total Sync API env (legacy -> runtime)" -Action {
        $env:HERMES_SKIP_PAUSE = '1'
        & (Join-Path $windowsRoot 'sync_hermes_api_env.ps1')
    }
} else {
    Write-Host "[SKIP] $step/$total Env sync (-SkipEnvSync)" -ForegroundColor Yellow
    Write-Host ''
}
$step++

if (-not $SkipE2E) {
    Invoke-Step -Name "$step/$total HermesHome E2E" -Action {
        & (Join-Path $windowsRoot 'audits\RUN_HERMES_HOME_E2E.ps1') -RepoRoot $repoRoot
    }
} else {
    Write-Host "[SKIP] $step/$total E2E (-SkipE2E)" -ForegroundColor Yellow
    Write-Host ''
}

Write-Host '=== HERMES SPLIT-HOME MIGRATIE: KLAAR ===' -ForegroundColor Green
Write-Host 'Start Hermes opnieuw: windows\launch_hermes.bat en /new in TUI.' -ForegroundColor Cyan
if (-not $NoPause -and -not ($env:HERMES_SKIP_PAUSE -in @('1', 'true', 'True'))) {
    Read-Host 'Druk Enter om af te sluiten'
}
exit 0
