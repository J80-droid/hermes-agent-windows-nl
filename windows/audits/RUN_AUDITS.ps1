# Hermes Windows fork — gecombineerde kwaliteitspoort (geen volledige upstream-kloon).
# PSScriptAnalyzer: SKIP als module ontbreekt (geen PSGallery-hang). Streng: -RequirePSScriptAnalyzer
# Repo-hygiene E2E (audits/): -IncludeRepoHygieneE2E, -IncludeInstitutionalHardeningE2E (+IncludeAllE2E),
#   -IncludeUpdateHermesIntegrationE2E (apart). Productie-poort: -IncludeInstitutionalProductionGate (~2+ min).
param(
    [switch]$RequirePSScriptAnalyzer,
    [switch]$IncludeProfileE2E,
    [switch]$IncludeInstitutionalE2E,
    [switch]$IncludeAllE2E,
    [switch]$IncludeLegalDomainE2E,
    [switch]$IncludeTrustForensicE2E,
    [switch]$IncludeToolsetDomainE2E,
    [switch]$IncludeProvisionDomainE2E,
    [switch]$IncludeSoulDeployStartE2E,
    [switch]$IncludePendingTrustStartE2E,
    [switch]$IncludeIdeMaintenanceE2E,
    [switch]$IncludeMemoryArchitectureE2E,
    [switch]$IncludeMemoryProductionGate,
    [switch]$IncludeMemoryRepairTrustE2E,
    [switch]$IncludeStatusBarCostE2E,
    [switch]$IncludeClassicCliStatusBarCostE2E,
    [switch]$IncludeParetoE2E,
    [switch]$IncludePseudoTableNormalizerE2E,
    [switch]$IncludeInstitutionalPipelineE2E,
    [switch]$IncludeHermesHomeE2E,
    [switch]$IncludeModelProviderCoherenceE2E,
    [switch]$IncludeModelProviderHardeningE2E,
    [switch]$IncludePythonInstitutionalE2E,
    [switch]$IncludeInstitutionalProductionGate,
    [switch]$IncludeRepoHygieneE2E,
    [switch]$IncludeInstitutionalHardeningE2E,
    [switch]$IncludeUpdateHermesIntegrationE2E,
    [switch]$IncludeSyncNousE2E,
    [switch]$IncludeNousOverlayInstitutionalE2E,
    [switch]$IncludeStatusBarThroughputE2E,
    [switch]$IncludePromptTimerDisplayE2E,
    [switch]$IncludeCodebaseSmoke,
    [switch]$IncludeCodebaseSmokeE2E,
    [switch]$SkipPytest,
    [switch]$SkipFootguns,
    [switch]$SkipRuff,
    [switch]$SkipVerifyChain,
    [switch]$SkipHermesPreflight
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
$scriptRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
Set-Location $repoRoot

$failures = 0
$skipped = 0

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action,
        [switch]$AllowSkip
    )
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    $stepFailed = $false
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Action
        $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
        if ($code -eq 0) {
            Write-Host ('[OK] ' + $Name) -ForegroundColor Green
        } elseif ($AllowSkip -and $code -eq 2) {
            Write-Host ('[SKIP] ' + $Name) -ForegroundColor Yellow
            $script:skipped++
        } else {
            Write-Host ('[FAIL] ' + $Name + ' (exit ' + $code + ')') -ForegroundColor Red
            $script:failures++
            $stepFailed = $true
        }
    } catch {
        Write-Host ('[FAIL] ' + $Name + ' (' + $($_.Exception.Message) + ')') -ForegroundColor Red
        $script:failures++
        $stepFailed = $true
    } finally {
        $ErrorActionPreference = $prevEap
    }
    return (-not $stepFailed)
}

if (-not $SkipHermesPreflight) {
    . (Join-Path $repoRoot 'windows/scripts/HermesHomeCommon.ps1')
    if ($env:HERMES_HOME -and (Test-HermesProfileSubdirPath $env:HERMES_HOME)) {
        Write-Host '[FAIL] HERMES_HOME wijst naar profiles\* — zet runtime-root (%LOCALAPPDATA%\hermes)' -ForegroundColor Red
        $failures++
    }

    $verify = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/scripts/verify_hermes_home.ps1'
    if (Test-Path -LiteralPath $verify) {
        Invoke-Step 'verify_hermes_home' { & $verify }
    }

    $verifyDrift = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/scripts/verify_hermes_config_drift.ps1'
    if (Test-Path -LiteralPath $verifyDrift) {
        Invoke-Step 'verify_hermes_config_drift' { & $verifyDrift }
    }
}

if (-not $SkipVerifyChain) {
    $chain = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/verify_windows_script_chain.ps1'
    if (Test-Path -LiteralPath $chain) {
        Invoke-Step 'verify_windows_chain' -AllowSkip {
            & $chain
        }
    }
}

$invokePsa = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/Invoke-HermesPSScriptAnalyzer.ps1'
if (Test-Path -LiteralPath $invokePsa) {
    $requirePsa = $RequirePSScriptAnalyzer.IsPresent
    Invoke-Step 'PSScriptAnalyzer' {
        $ifMissing = if ($requirePsa) { 'Fail' } else { 'Skip' }
        . $invokePsa
        $code = Invoke-HermesPSScriptAnalyzer -RepoRoot $repoRoot -IfMissing $ifMissing
        $global:LASTEXITCODE = $code
    }
}

if (-not $SkipFootguns) {
    $footguns = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'scripts/check-windows-footguns.py'
    if (Test-Path -LiteralPath $footguns) {
        Invoke-Step 'windows-footguns' {
            $py = Get-HermesAuditPython -RepoRoot $repoRoot
            & $py $footguns --all
            $global:LASTEXITCODE = $LASTEXITCODE
        }
    }
}

if (-not $SkipRuff) {
    Invoke-Step 'ruff' -AllowSkip {
        $ruff = Get-Command ruff -ErrorAction SilentlyContinue
        if (-not $ruff) {
            Write-Host 'SKIP: ruff niet op PATH' -ForegroundColor Yellow
            $global:LASTEXITCODE = 2
            return
        }
        & ruff check `
            hermes_cli/profile_switch.py `
            hermes_cli/relaunch.py `
            hermes_cli/main.py `
            cli.py `
            tests/hermes_cli/test_profile_switch.py `
            tests/hermes_cli/test_apply_profile_override.py `
            tests/hermes_cli/test_relaunch.py
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeAllE2E) {
    $syncSouls = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/scripts/sync_all_domain_souls_from_templates.ps1'
    Invoke-Step 'soul-runtime-prep' {
        $prevReminder = $env:HERMES_SUPPRESS_SOUL_REMINDER
        $env:HERMES_SUPPRESS_SOUL_REMINDER = '1'
        try {
            & $syncSouls -RepoRoot $repoRoot -UpdateDeployStamp
            $global:LASTEXITCODE = $LASTEXITCODE
        } finally {
            if ($null -eq $prevReminder) {
                Remove-Item Env:HERMES_SUPPRESS_SOUL_REMINDER -ErrorAction SilentlyContinue
            } else {
                $env:HERMES_SUPPRESS_SOUL_REMINDER = $prevReminder
            }
        }
    }
}

if ($IncludeCodebaseSmokeE2E -or $IncludeAllE2E) {
    $codebaseE2e = Join-Path $scriptRoot 'RUN_CODEBASE_SMOKE_E2E.ps1'
    Invoke-Step 'codebase-smoke-e2e' {
        & $codebaseE2e -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
} elseif ($IncludeCodebaseSmoke) {
    $smoke = Join-Path $scriptRoot 'RUN_CODEBASE_SMOKE_AUDIT.ps1'
    Invoke-Step 'codebase-smoke-audit' {
        & $smoke -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if (-not (Get-Command Test-HermesProfileSubdirPath -ErrorAction SilentlyContinue)) {
    . (Join-Path $repoRoot 'windows/scripts/HermesHomeCommon.ps1')
}

$runtimeHermesHome = Join-Path $env:LOCALAPPDATA 'hermes'
$env:HERMES_HOME = $runtimeHermesHome

function Get-HermesAuditPythonExe {
    $condaPy = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if (Test-Path -LiteralPath $condaPy) { return $condaPy }
    return 'python'
}

if (-not $SkipPytest) {
    Invoke-Step 'pytest-overlay' {
        $py = Get-HermesAuditPythonExe
        $env:HERMES_HOME = $runtimeHermesHome
        & $py -m pytest tests/overlay/ -q -o addopts= --tb=short
        $global:LASTEXITCODE = $LASTEXITCODE
    }

    Invoke-Step 'pytest-profile-subset' {
        $py = Get-HermesAuditPythonExe
        if ($py -eq 'python' -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
            Write-Host 'SKIP: python niet gevonden' -ForegroundColor Yellow
            $global:LASTEXITCODE = 2
            return
        }
        $env:HERMES_HOME = $runtimeHermesHome
        & $py -m pytest `
            tests/hermes_cli/test_apply_profile_override.py `
            tests/hermes_cli/test_profile_switch.py `
            tests/hermes_cli/test_relaunch.py::TestRelaunchChatAfterProfileSwitch `
            tests/hermes_cli/test_relaunch.py::TestStripProfileFlags `
            -q -o addopts= --tb=short
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeIdeMaintenanceE2E -or $IncludeAllE2E) {
    $ideE2e = Join-Path $scriptRoot 'RUN_IDE_MAINTENANCE_E2E.ps1'
    Invoke-Step 'ide-maintenance-e2e' {
        $ideArgs = @{ ApplyDisplayFix = $true }
        if ($IncludeAllE2E) {
            $ideArgs['SkipMergePreview'] = $true
        }
        & $ideE2e @ideArgs
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeInstitutionalE2E -or $IncludeAllE2E) {
    $instE2e = Join-Path $scriptRoot 'RUN_INSTITUTIONAL_E2E.ps1'
    Invoke-Step 'institutional-e2e' {
        & $instE2e
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeLegalDomainE2E -or $IncludeAllE2E) {
    $legalUnit = Join-Path $repoRoot 'windows\tests\LegalDomainE2E.Unit.Tests.ps1'
    Invoke-Step 'legal-domain-e2e-unit' {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $legalUnit
        $global:LASTEXITCODE = $LASTEXITCODE
    }
    $legalE2e = Join-Path $scriptRoot 'RUN_LEGAL_DOMAIN_E2E.ps1'
    Invoke-Step 'legal-domain-e2e' {
        & $legalE2e
        $global:LASTEXITCODE = $LASTEXITCODE
    }
    $proactivePs1 = Join-Path $repoRoot 'windows/scripts/Invoke-LegalProactiveSparringE2E.ps1'
    Invoke-Step 'legal-proactive-sparring-e2e' {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $proactivePs1 -RepoRoot $repoRoot -Context Manual
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeProfileE2E -or $IncludeAllE2E) {
    $e2e = Join-Path $scriptRoot 'RUN_PROFILE_SWITCH_E2E.ps1'
    Invoke-Step 'profile-switch-e2e' {
        & $e2e
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeTrustForensicE2E -or $IncludeAllE2E) {
    $trustE2e = Join-Path $scriptRoot 'RUN_TRUST_FORENSIC_E2E.ps1'
    Invoke-Step 'trust-forensic-e2e' {
        & $trustE2e
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeProvisionDomainE2E -or $IncludeAllE2E) {
    $provE2e = Join-Path $scriptRoot 'RUN_PROVISION_DOMAIN_E2E.ps1'
    Invoke-Step 'provision-domain-e2e' {
        & $provE2e -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeToolsetDomainE2E -or $IncludeAllE2E) {
    $toolE2e = Join-Path $scriptRoot 'RUN_TOOLSET_DOMAIN_E2E.ps1'
    Invoke-Step 'toolset-domain-e2e' {
        & $toolE2e -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeSoulDeployStartE2E -or $IncludeAllE2E) {
    $soulStartE2e = Join-Path $scriptRoot 'RUN_SOUL_DEPLOY_START_E2E.ps1'
    Invoke-Step 'soul-deploy-start-e2e' {
        & $soulStartE2e -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludePendingTrustStartE2E -or $IncludeAllE2E) {
    $pendingTrustE2e = Join-Path $scriptRoot 'RUN_PENDING_TRUST_START_E2E.ps1'
    Invoke-Step 'pending-trust-start-e2e' {
        & $pendingTrustE2e -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeMemoryArchitectureE2E -or $IncludeAllE2E) {
    $memE2e = Join-Path $scriptRoot 'RUN_MEMORY_ARCHITECTURE_E2E.ps1'
    Invoke-Step 'memory-architecture-e2e' {
        & $memE2e -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeMemoryProductionGate -or $IncludeAllE2E) {
    $memGate = Join-Path $scriptRoot 'RUN_MEMORY_PRODUCTION_GATE.ps1'
    Invoke-Step 'memory-production-gate' {
        & $memGate -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeMemoryRepairTrustE2E -or $IncludeAllE2E) {
    $memRepairE2e = Join-Path $repoRoot 'audits\RUN_MEMORY_REPAIR_TRUST_E2E.bat'
    Invoke-Step 'memory-repair-trust-e2e' {
        & cmd /c "`"$memRepairE2e`""
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeStatusBarCostE2E -or $IncludeAllE2E) {
    $costE2e = Join-Path $scriptRoot 'RUN_STATUS_BAR_COST_E2E.ps1'
    Invoke-Step 'status-bar-cost-e2e' {
        & $costE2e -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeClassicCliStatusBarCostE2E -or $IncludeAllE2E) {
    $classicCostE2e = Join-Path $scriptRoot 'RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1'
    $classicArgs = @{ RepoRoot = $repoRoot }
    if ($SkipPytest) { $classicArgs['SkipPytest'] = $true }
    Invoke-Step 'classic-cli-status-bar-cost-e2e' {
        & $classicCostE2e @classicArgs
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeParetoE2E -or $IncludeAllE2E) {
    $paretoE2e = Join-Path $scriptRoot 'RUN_PARETO_E2E.ps1'
    Invoke-Step 'pareto-e2e' {
        & $paretoE2e -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludePseudoTableNormalizerE2E -or $IncludeAllE2E) {
    $pseudoE2e = Join-Path $scriptRoot 'RUN_PSEUDO_TABLE_NORMALIZER_E2E.ps1'
    Invoke-Step 'pseudo-table-normalizer-e2e' {
        & $pseudoE2e -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeInstitutionalPipelineE2E -or $IncludeAllE2E) {
    $pipelineE2e = Join-Path $repoRoot 'audits\InstitutionalPipelineE2E.core.ps1'
    Invoke-Step 'institutional-pipeline-e2e' {
        & $pipelineE2e -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeHermesHomeE2E -or $IncludeAllE2E) {
    $homeE2e = Join-Path $scriptRoot 'RUN_HERMES_HOME_E2E.ps1'
    Invoke-Step 'hermes-home-e2e' {
        & $homeE2e -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeModelProviderCoherenceE2E -or $IncludeAllE2E) {
    $coherenceE2e = Join-Path $scriptRoot 'RUN_MODEL_PROVIDER_COHERENCE_E2E.bat'
    Invoke-Step 'model-provider-coherence-e2e' {
        & $coherenceE2e
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeModelProviderHardeningE2E -or $IncludeAllE2E) {
    $hardeningE2e = Join-Path $scriptRoot 'RUN_MODEL_PROVIDER_HARDENING_E2E.bat'
    Invoke-Step 'model-provider-hardening-e2e' {
        & $hardeningE2e
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludePythonInstitutionalE2E -or $IncludeAllE2E) {
    $pyInst = Join-Path $scriptRoot 'RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.ps1'
    Invoke-Step 'hermes-python-institutional-e2e' {
        & $pyInst -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeRepoHygieneE2E) {
    $repoHygieneBat = Join-Path $repoRoot 'audits\RUN_REPO_HYGIENE_E2E.bat'
    Invoke-Step 'repo-hygiene-e2e' {
        cmd /c "`"$repoHygieneBat`""
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeInstitutionalHardeningE2E -or $IncludeAllE2E) {
    $instHardeningBat = Join-Path $repoRoot 'audits\RUN_INSTITUTIONAL_HARDENING_E2E.bat'
    Invoke-Step 'institutional-hardening-e2e' {
        cmd /c "`"$instHardeningBat`""
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeUpdateHermesIntegrationE2E) {
    $updateIntBat = Join-Path $repoRoot 'audits\RUN_UPDATE_HERMES_INTEGRATION_E2E.bat'
    Invoke-Step 'update-hermes-integration-e2e' {
        cmd /c "`"$updateIntBat`""
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeSyncNousE2E -or $IncludeAllE2E) {
    $syncNousBat = Join-Path $scriptRoot 'RUN_SYNC_NOUS_E2E.bat'
    Invoke-Step 'sync-nous-e2e' {
        cmd /c "`"$syncNousBat`""
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeNousOverlayInstitutionalE2E -or $IncludeAllE2E) {
    if (-not $env:HERMES_HOME) {
        $env:HERMES_HOME = Join-Path $env:LOCALAPPDATA 'hermes'
    }
    $restoreTierA = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/scripts/Invoke-RestoreNousTierA.ps1'
    $nousOverlayBat = Join-Path $repoRoot 'audits\RUN_NOUS_OVERLAY_INSTITUTIONAL_E2E.bat'
    Invoke-Step 'nous-overlay-institutional-e2e' {
        if (Test-Path -LiteralPath $restoreTierA) {
            & $restoreTierA
        }
        cmd /c "`"$nousOverlayBat`""
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeStatusBarThroughputE2E -or $IncludeAllE2E) {
    $throughputBat = Join-Path $repoRoot 'audits\RUN_STATUS_BAR_THROUGHPUT_E2E.bat'
    Invoke-Step 'status-bar-throughput-e2e' {
        cmd /c "`"$throughputBat`""
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludePromptTimerDisplayE2E -or $IncludeAllE2E) {
    $promptTimerBat = Join-Path $repoRoot 'audits\RUN_PROMPT_TIMER_DISPLAY_E2E.bat'
    Invoke-Step 'prompt-timer-display-e2e' {
        cmd /c "`"$promptTimerBat`""
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeInstitutionalProductionGate) {
    $instGate = Join-Path $scriptRoot 'RUN_INSTITUTIONAL_PRODUCTION_GATE.ps1'
    Invoke-Step 'institutional-production-gate' {
        & $instGate -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

Write-Host ""
if ($failures -gt 0) {
    Write-Host "RUN_AUDITS: $failures stap(pen) gefaald, $skipped overgeslagen." -ForegroundColor Red
    exit 1
}
Write-Host "RUN_AUDITS: alles geslaagd ($skipped overgeslagen)." -ForegroundColor Green
exit 0
