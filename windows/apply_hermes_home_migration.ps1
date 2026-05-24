<#
.SYNOPSIS
    Eénmalige split-home migratie: backup → deprecate legacy config → auxiliary preset → E2E.
.DESCRIPTION
    Idempotent waar mogelijk. Deprecate is no-op als legacy config.yaml al gearchiveerd is.
    Backup vereist dat Hermes/gateway volledig gestopt zijn (behalve met -SkipBackup).
.PARAMETER SkipBackup
    Sla backup over (her-run na eerdere MANAGE_BACKUPS).
.PARAMETER SkipDeprecate
    Sla deprecate over (legacy al gearchiveerd).
.PARAMETER SkipAuxiliary
    Sla auxiliary preset over.
.PARAMETER SkipE2E
    Sla RUN_HERMES_HOME_E2E over.
.PARAMETER NoCopyAuxiliaryOnly
    Deprecate zonder selectieve auxiliary-merge (standaard: -CopyAuxiliaryOnly).
.PARAMETER NoPause
    Geen pause aan het einde.
#>
param(
    [switch]$SkipBackup,
    [switch]$SkipDeprecate,
    [switch]$SkipAuxiliary,
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
if ($NoCopyAuxiliaryOnly) {
    Write-Host '[INFO] Deprecate zonder -CopyAuxiliaryOnly' -ForegroundColor Cyan
}
Write-Host '[INFO] Keten: backup -> deprecate -> auxiliary preset -> E2E' -ForegroundColor Cyan
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

if (-not $SkipBackup) {
    Invoke-Step -Name '1/4 Backup (MANAGE_BACKUPS)' -Action {
        $env:HERMES_BACKUP_NONINTERACTIVE = '1'
        & (Join-Path $windowsRoot 'backup_hermes.ps1') -SkipPause
    }
} else {
    Write-Host '[SKIP] 1/4 Backup (-SkipBackup)' -ForegroundColor Yellow
    Write-Host ''
}

if (-not $SkipDeprecate) {
    Invoke-Step -Name '2/4 Deprecate legacy config' -Action {
        if (-not $NoCopyAuxiliaryOnly) {
            & (Join-Path $windowsRoot 'scripts\deprecate_legacy_config.ps1') -CopyAuxiliaryOnly
        } else {
            & (Join-Path $windowsRoot 'scripts\deprecate_legacy_config.ps1')
        }
    }
} else {
    Write-Host '[SKIP] 2/4 Deprecate (-SkipDeprecate)' -ForegroundColor Yellow
    Write-Host ''
}

if (-not $SkipAuxiliary) {
    Invoke-Step -Name '3/4 Auxiliary hybrid preset' -Action {
        & (Join-Path $windowsRoot 'scripts\apply_auxiliary_hybrid_preset.ps1')
    }
} else {
    Write-Host '[SKIP] 3/4 Auxiliary (-SkipAuxiliary)' -ForegroundColor Yellow
    Write-Host ''
}

if (-not $SkipE2E) {
    Invoke-Step -Name '4/4 HermesHome E2E' -Action {
        & (Join-Path $windowsRoot 'audits\RUN_HERMES_HOME_E2E.ps1') -RepoRoot $repoRoot
    }
} else {
    Write-Host '[SKIP] 4/4 E2E (-SkipE2E)' -ForegroundColor Yellow
    Write-Host ''
}

Write-Host '=== HERMES SPLIT-HOME MIGRATIE: KLAAR ===' -ForegroundColor Green
Write-Host 'Start Hermes opnieuw: windows\launch_hermes.bat en /new in TUI.' -ForegroundColor Cyan
if (-not $NoPause -and -not ($env:HERMES_SKIP_PAUSE -in @('1', 'true', 'True'))) {
    Read-Host 'Druk Enter om af te sluiten'
}
exit 0
