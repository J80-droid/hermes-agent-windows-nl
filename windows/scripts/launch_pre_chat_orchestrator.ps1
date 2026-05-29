# Structurele pre-chat launch: alle PS-fases met voortgang, geen boolean-leak naar cmd.
param(
    [string]$RepoRoot = '',
    [switch]$RunInstitutionalE2E,
    [switch]$SkipBootstrap
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'HermesHomeCommon.ps1')

function Get-NormalizedHermesRepoRoot {
    param([string]$Candidate = '')
    $raw = if ($Candidate) { $Candidate } elseif ($env:HERMES_REPO_ROOT) { $env:HERMES_REPO_ROOT } else { '' }
    $raw = "$raw".Trim().Trim([char]34, [char]39, [char]0x201C, [char]0x201D)
    if (-not $raw) {
        throw 'RepoRoot ontbreekt — zet HERMES_REPO_ROOT of geef -RepoRoot door.'
    }
    return (Resolve-Path -LiteralPath $raw).Path
}

$RepoRoot = Get-NormalizedHermesRepoRoot -Candidate $RepoRoot
$env:HERMES_REPO_ROOT = $RepoRoot
if ($env:HERMES_LAUNCH_LOG) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -LiteralPath $env:HERMES_LAUNCH_LOG -Value "[$ts] Pre-chat orchestrator start" -Encoding UTF8 -ErrorAction SilentlyContinue
}

$total = 0
if (-not $SkipBootstrap) { $total++ }
if ($env:HERMES_MINIMAL_LAUNCH -ne '1') { $total++ }
if ($env:HERMES_SKIP_SOUL_DEPLOY_ON_START -ne '1') { $total++ }
if ($env:HERMES_SKIP_TRUST_RUNTIME_ON_START -ne '1') { $total++ }
if ($env:HERMES_SKIP_INSTITUTIONAL_RUNTIME -ne '1') { $total++ }
if ($env:HERMES_SKIP_PENDING_TRUST_ON_START -ne '1') { $total++ }
if ($env:HERMES_SKIP_DASHBOARD_ON_START -ne '1') {
    if (-not $env:HERMES_DASHBOARD_ON_START) { $env:HERMES_DASHBOARD_ON_START = '1' }
    if ($env:HERMES_DASHBOARD_ON_START -ne '0') { $total++ }
}
if ($total -lt 1) { $total = 1 }

$step = 0
$maintenancePath = Join-Path $PSScriptRoot 'HermesSessionMaintenance.ps1'

[void](Stop-HermesGhostInputBlockers -RepoRoot $RepoRoot)

if (-not $SkipBootstrap) {
    $step++
    $bootstrap = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_bootstrap.ps1'
    Invoke-HermesLaunchPhase -Step $step -Total $total -Label 'Bootstrap (conda / RAG-stamp)' -Action {
        [void](& $bootstrap -RepoRoot $RepoRoot)
    }
}

if ($env:HERMES_MINIMAL_LAUNCH -ne '1') {
    $step++
    Invoke-HermesLaunchPhase -Step $step -Total $total -Label 'Sessie-onderhoud (start)' -AllowFailure -Action {
        . $maintenancePath -RepoRoot $RepoRoot -AllowFailure
        [void](Invoke-HermesStartMaintenance)
    }
}

if ($env:HERMES_SKIP_SOUL_DEPLOY_ON_START -ne '1') {
    $step++
    $soul = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_soul_anatomy_deploy.ps1'
    Invoke-HermesLaunchPhase -Step $step -Total $total -Label 'SOUL anatomy deploy' -AllowFailure -Action {
        [void](& $soul -RepoRoot $RepoRoot)
    }
}

if ($env:HERMES_SKIP_TRUST_RUNTIME_ON_START -ne '1') {
    $step++
    $trustSync = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_trust_runtime_sync.ps1'
    Invoke-HermesLaunchPhase -Step $step -Total $total -Label 'Trust/memory sync (indien nodig)' -AllowFailure -Action {
        [void](& $trustSync -RepoRoot $RepoRoot -Quiet)
    }
}

if ($env:HERMES_SKIP_INSTITUTIONAL_RUNTIME -ne '1') {
    $step++
    $inst = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_institutional_runtime.ps1'
    $instArgs = @{ RepoRoot = $RepoRoot; SkipConfigDrift = $true }
    if ($RunInstitutionalE2E) { $instArgs['RunE2E'] = $true }
    elseif ($env:HERMES_INSTITUTIONAL_E2E_ON_START -eq '1') { $instArgs['RunE2E'] = $true }
    Invoke-HermesLaunchPhase -Step $step -Total $total -Label 'Institutioneel runtime (display)' -AllowFailure -Action {
        [void](& $inst @instArgs)
    }
}

if ($env:HERMES_SKIP_PENDING_TRUST_ON_START -ne '1') {
    $step++
    $trust = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_pending_trust_runtime.ps1'
    Invoke-HermesLaunchPhase -Step $step -Total $total -Label 'Trust-nazorg (indien nodig)' -AllowFailure -Action {
        [void](& $trust -RepoRoot $RepoRoot -Quiet)
    }
}

if ($env:HERMES_SKIP_DASHBOARD_ON_START -ne '1') {
    if (-not $env:HERMES_DASHBOARD_ON_START) { $env:HERMES_DASHBOARD_ON_START = '1' }
    if ($env:HERMES_DASHBOARD_ON_START -ne '0') {
        $step++
        $dash = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_dashboard_on_start.ps1'
        $prevQuick = $env:HERMES_DASHBOARD_QUICK_START
        if (-not $RunInstitutionalE2E) { $env:HERMES_DASHBOARD_QUICK_START = '1' }
        try {
            Invoke-HermesLaunchPhase -Step $step -Total $total -Label 'Web dashboard (achtergrond)' -AllowFailure -Action {
                [void](& $dash -RepoRoot $RepoRoot -Quiet)
            }
        } finally {
            if ($null -eq $prevQuick) {
                Remove-Item Env:HERMES_DASHBOARD_QUICK_START -ErrorAction SilentlyContinue
            } else {
                $env:HERMES_DASHBOARD_QUICK_START = $prevQuick
            }
        }
    }
}

exit 0
