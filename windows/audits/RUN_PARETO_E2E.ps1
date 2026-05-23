# OpenRouter Pareto Code router E2E (model-gated min_coding_score wiring).
# Syntax-check: windows/tests/Validate-AuditPs1Syntax.ps1
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest
)

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$failures = 0
$steps = [System.Collections.Generic.List[object]]::new()

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
    foreach ($candidate in @(
            'C:\Users\jamel\AppData\Local\Programs\Python\Python312\python.exe',
            'python'
        )) {
        if ($candidate -eq 'python' -or (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }
    return 'python'
}

function Add-StepResult {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    $steps.Add([pscustomobject]@{ Step = $Name; Ok = $Ok; Detail = $Detail })
    if ($Ok) {
        Write-Host ('[OK] ' + $Name + $(if ($Detail) { ' - ' + $Detail } else { '' })) -ForegroundColor Green
    } else {
        Write-Host ('[FAIL] ' + $Name + $(if ($Detail) { ' - ' + $Detail } else { '' })) -ForegroundColor Red
        $script:failures++
    }
}

function Invoke-AuditCommand {
    param(
        [Parameter(Mandatory)][string]$Exe,
        [string[]]$ArgumentList = @()
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $out = & $Exe @ArgumentList 2>&1
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEap
    foreach ($line in @($out)) {
        if ($null -ne $line -and "$line".Trim()) {
            Write-Host $line
        }
    }
    return $ok
}

Write-Host '=== Pareto Code Router E2E ===' -ForegroundColor Cyan
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

# --- 1 Repo artefacten ---
$repoFiles = @(
    'plugins/model-providers/openrouter/__init__.py',
    'agent/transports/chat_completions.py',
    'agent/chat_completion_helpers.py',
    'hermes_cli/config.py',
    'hermes_cli/models.py',
    'scripts/verify_pareto_router.py',
    'tests/windows/test_pareto_e2e.py',
    'windows/audits/RUN_PARETO_E2E.ps1'
)
$repoOk = $true
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot ($rel -replace '/', '\')))) {
        $repoOk = $false
        break
    }
}
Add-StepResult -Name '1/8 repo pareto wiring files' -Ok $repoOk

# --- 2 OpenRouter plugin model-gate ---
$pluginPath = Join-Path $RepoRoot 'plugins/model-providers/openrouter/__init__.py'
$pluginText = Get-Content -LiteralPath $pluginPath -Raw -Encoding UTF8
$pluginOk = ($pluginText -match 'openrouter/pareto-code') -and ($pluginText -match 'pareto-router') -and ($pluginText -match 'min_coding_score')
Add-StepResult -Name '2/8 openrouter plugin model-gate' -Ok $pluginOk

# --- 3 Transport + summary helper parity ---
$transportText = Get-Content -LiteralPath (Join-Path $RepoRoot 'agent/transports/chat_completions.py') -Raw -Encoding UTF8
$helpersText = Get-Content -LiteralPath (Join-Path $RepoRoot 'agent/chat_completion_helpers.py') -Raw -Encoding UTF8
$parityOk = ($transportText -match 'pareto-router') -and ($helpersText -match 'pareto-router') -and ($transportText -match 'openrouter/pareto-code') -and ($helpersText -match 'openrouter/pareto-code')
Add-StepResult -Name '3/8 transport + summary parity' -Ok $parityOk

# --- 4 Config template + model catalog ---
$configText = Get-Content -LiteralPath (Join-Path $RepoRoot 'hermes_cli/config.py') -Raw -Encoding UTF8
$modelsText = Get-Content -LiteralPath (Join-Path $RepoRoot 'hermes_cli/models.py') -Raw -Encoding UTF8
$configOk = ($configText -match 'min_coding_score') -and ($configText -match 'openrouter/pareto-code') -and ($modelsText -match 'openrouter/pareto-code')
Add-StepResult -Name '4/8 config + model catalog' -Ok $configOk

# --- 5 Pytest keten ---
if ($SkipPytest) {
    Add-StepResult -Name '5/8 pytest pareto transport' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
    Add-StepResult -Name '6/8 pytest pareto e2e + profiles' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $transportOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-Path $RepoRoot 'tests/agent/transports/test_chat_completions.py'),
        '-k', 'openrouter_pareto',
        '-q',
        '-o', 'addopts='
    )
    Add-StepResult -Name '5/8 pytest pareto transport' -Ok $transportOk -Detail $python

    $moduleOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-Path $RepoRoot 'tests/windows/test_pareto_e2e.py'),
        (Join-Path $RepoRoot 'tests/providers/test_provider_profiles.py'),
        '-k', 'pareto',
        '-q',
        '-o', 'addopts='
    )
    Add-StepResult -Name '6/8 pytest pareto e2e + profiles' -Ok $moduleOk
}

# --- 7 Verify script ---
$verifyPy = Join-Path $RepoRoot 'scripts/verify_pareto_router.py'
$verifyOk = Invoke-AuditCommand -Exe $python -ArgumentList @($verifyPy, '--verify')
Add-StepResult -Name '7/8 verify_pareto_router' -Ok $verifyOk

# --- 8 Documentatie ---
$providersMd = Join-Path $RepoRoot 'website/docs/integrations/providers.md'
$configMd = Join-Path $RepoRoot 'website/docs/user-guide/configuration.md'
$docsOk = $false
if ((Test-Path -LiteralPath $providersMd) -and (Test-Path -LiteralPath $configMd)) {
    $providersText = Get-Content -LiteralPath $providersMd -Raw -Encoding UTF8
    $configDocText = Get-Content -LiteralPath $configMd -Raw -Encoding UTF8
    $docsOk = ($providersText -match 'Pareto') -and ($providersText -match 'pareto-code') -and ($configDocText -match 'Pareto|pareto-router|pareto-code')
}
Add-StepResult -Name '8/8 docs providers + configuration' -Ok $docsOk

# --- Rapport ---
$reportFileName = 'PARETO_E2E_REPORT_' + $reportStamp + '.md'
$reportPath = Join-Path $scriptRoot $reportFileName
$status = if ($failures -eq 0) { 'PASS' } else { 'FAIL' }
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Pareto Code Router E2E - $status")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$sb.AppendLine("Repo: ``$RepoRoot``")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('| Stap | Status | Detail |')
[void]$sb.AppendLine('|------|--------|--------|')
foreach ($s in $steps) {
    $st = if ($s.Ok) { 'PASS' } else { 'FAIL' }
    $det = ($s.Detail -replace '\|', '/') -replace "`r?`n", ' '
    [void]$sb.AppendLine("| $($s.Step) | $st | $det |")
}
[void]$sb.AppendLine('')
if ($failures -gt 0) {
    [void]$sb.AppendLine("**$failures** stap(pen) gefaald. Controleer openrouter plugin, chat_completions en pytest pareto tests.")
} else {
    [void]$sb.AppendLine('Alle stappen geslaagd. Pareto router is model-gated op openrouter/pareto-code.')
}
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host ''
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== PARETO E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== PARETO E2E: PASS ===' -ForegroundColor Green
exit 0
