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
    [switch]$IncludeIdeMaintenanceE2E,
    [switch]$SkipPytest,
    [switch]$SkipFootguns,
    [switch]$SkipRuff,
    [switch]$SkipVerifyChain
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
Set-Location $repoRoot

$failures = 0
$skipped = 0

function Get-HermesAuditPython {
    if ($env:HERMES_AUDIT_PYTHON -and (Test-Path -LiteralPath $env:HERMES_AUDIT_PYTHON)) {
        return $env:HERMES_AUDIT_PYTHON
    }
    $conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
    if (Test-Path -LiteralPath $conda) {
        $out = & $conda run -n hermes-env python -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            return ($out | Select-Object -Last 1).ToString().Trim()
        }
    }
    return 'python'
}

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

$verify = Join-Path $repoRoot 'windows/scripts/verify_hermes_home.ps1'
if (Test-Path -LiteralPath $verify) {
    Invoke-Step 'verify_hermes_home' { & $verify }
}

if (-not $SkipVerifyChain) {
    $chain = Join-Path $repoRoot 'windows/verify_windows_script_chain.ps1'
    if (Test-Path -LiteralPath $chain) {
        Invoke-Step 'verify_windows_chain' -AllowSkip {
            & $chain
        }
    }
}

$invokePsa = Join-Path $repoRoot 'windows/Invoke-HermesPSScriptAnalyzer.ps1'
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
    $footguns = Join-Path $repoRoot 'scripts/check-windows-footguns.py'
    if (Test-Path -LiteralPath $footguns) {
        Invoke-Step 'windows-footguns' {
            $py = Get-HermesAuditPython
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

Write-Host ""
if ($failures -gt 0) {
    Write-Host "RUN_AUDITS: $failures stap(pen) gefaald, $skipped overgeslagen." -ForegroundColor Red
    exit 1
}
Write-Host "RUN_AUDITS: alles geslaagd ($skipped overgeslagen)." -ForegroundColor Green
exit 0
