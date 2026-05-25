# Hermes Windows fork — gecombineerde kwaliteitspoort (geen volledige upstream-kloon).
# PSScriptAnalyzer: SKIP als module ontbreekt (geen PSGallery-hang). Streng: -RequirePSScriptAnalyzer
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
    [switch]$IncludeStatusBarCostE2E,
    [switch]$IncludeClassicCliStatusBarCostE2E,
    [switch]$IncludeParetoE2E,
    [switch]$IncludePseudoTableNormalizerE2E,
    [switch]$IncludeHermesHomeE2E,
    [switch]$IncludePythonInstitutionalE2E,
    [switch]$IncludeInstitutionalProductionGate,
    [switch]$IncludeCodebaseSmoke,
    [switch]$IncludeCodebaseSmokeE2E,
    [switch]$SkipPytest,
    [switch]$SkipFootguns,
    [switch]$SkipRuff,
    [switch]$SkipVerifyChain
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
    }
    return (-not $stepFailed)
}

$verify = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/scripts/verify_hermes_home.ps1'
if (Test-Path -LiteralPath $verify) {
    Invoke-Step 'verify_hermes_home' { & $verify }
}

$verifyDrift = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/scripts/verify_hermes_config_drift.ps1'
if (Test-Path -LiteralPath $verifyDrift) {
    Invoke-Step 'verify_hermes_config_drift' { & $verifyDrift }
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

if (-not $SkipPytest) {
    Invoke-Step 'pytest-profile-subset' {
        $conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
        if (-not (Test-Path -LiteralPath $conda)) {
            Write-Host 'SKIP: conda niet gevonden' -ForegroundColor Yellow
            $global:LASTEXITCODE = 2
            return
        }
        & $conda run -n hermes-env --no-capture-output python -m pytest `
            tests/hermes_cli/test_apply_profile_override.py `
            tests/hermes_cli/test_profile_switch.py `
            tests/hermes_cli/test_relaunch.py::TestRelaunchChatAfterProfileSwitch `
            tests/hermes_cli/test_relaunch.py::TestStripProfileFlags `
            -q --tb=short
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeIdeMaintenanceE2E -or $IncludeAllE2E) {
    $ideE2e = Join-Path $scriptRoot 'RUN_IDE_MAINTENANCE_E2E.ps1'
    Invoke-Step 'ide-maintenance-e2e' {
        & $ideE2e -ApplyDisplayFix
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
    $legalE2e = Join-Path $scriptRoot 'RUN_LEGAL_DOMAIN_E2E.ps1'
    Invoke-Step 'legal-domain-e2e' {
        & $legalE2e
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

if ($IncludeStatusBarCostE2E -or $IncludeAllE2E) {
    $costE2e = Join-Path $scriptRoot 'RUN_STATUS_BAR_COST_E2E.ps1'
    Invoke-Step 'status-bar-cost-e2e' {
        & $costE2e -RepoRoot $repoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludeClassicCliStatusBarCostE2E -or $IncludeAllE2E) {
    $classicCostE2e = Join-Path $scriptRoot 'RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1'
    Invoke-Step 'classic-cli-status-bar-cost-e2e' {
        & $classicCostE2e -RepoRoot $repoRoot
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

if ($IncludeHermesHomeE2E -or $IncludeAllE2E) {
    $homeE2e = Join-Path $scriptRoot 'RUN_HERMES_HOME_E2E.ps1'
    Invoke-Step 'hermes-home-e2e' {
        & $homeE2e -RepoRoot $repoRoot
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
