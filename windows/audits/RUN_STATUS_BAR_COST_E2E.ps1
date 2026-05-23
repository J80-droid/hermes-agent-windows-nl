# Status-bar session cost E2E (show_cost team default + gateway usage + TUI helpers).
param(
    [string]$RepoRoot = '',
    [switch]$SkipVitest,
    [switch]$ApplyDisplayFix
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

function Get-HermesRoot {
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

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

Write-Host '=== Status Bar Cost E2E ===' -ForegroundColor Cyan
$hermesRoot = Get-HermesRoot
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

if ($ApplyDisplayFix) {
    Write-Host '--- apply_team_display (optioneel) ---' -ForegroundColor Cyan
    & (Join-Path $RepoRoot 'windows/apply_team_display.ps1')
    if (Test-NativeCommandFailed) {
        Add-StepResult -Name '0/8 apply_team_display' -Ok $false
    } else {
        Add-StepResult -Name '0/8 apply_team_display' -Ok $true
    }
}

# --- 1 Repo defaults + UI wiring ---
$defaultsPath = Join-Path $RepoRoot 'windows/team_display.defaults'
$defaultsText = if (Test-Path -LiteralPath $defaultsPath) {
    Get-Content -LiteralPath $defaultsPath -Raw -Encoding UTF8
} else { '' }
$repoOk = ($defaultsText -match 'show_cost=true')
$repoFiles = @(
    'ui-tui/src/domain/usage.ts',
    'ui-tui/src/components/appChrome.tsx',
    'ui-tui/src/app/slash/commands/core.ts',
    'tui_gateway/server.py',
    'scripts/status_bar_cost_gateway_smoke.py',
    'windows/audits/RUN_STATUS_BAR_COST_E2E.ps1'
)
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot ($rel -replace '/', '\')))) {
        $repoOk = $false
        break
    }
}
Add-StepResult -Name '1/8 repo defaults + artefacten' -Ok $repoOk -Detail 'team_display.defaults show_cost=true'

# --- 2 Guardrails in institutional / diagnose scripts ---
$instE2e = Get-Content -LiteralPath (Join-Path $RepoRoot 'windows/audits/RUN_INSTITUTIONAL_E2E.ps1') -Raw -Encoding UTF8
$diagPy = Get-Content -LiteralPath (Join-Path $RepoRoot 'scripts/diagnose_renderer.py') -Raw -Encoding UTF8
$guardOk = ($instE2e -match 'show_cost=true') -and ($diagPy -match 'show_cost')
Add-StepResult -Name '2/8 institutional + diagnose drift guards' -Ok $guardOk

# --- 3 Vitest statusBarCost ---
if (-not $SkipVitest) {
    Push-Location (Join-Path $RepoRoot 'ui-tui')
    try {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        npm test -- statusBarCost --run *>&1 | Out-Host
        $vitestOk = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $prevEap
    } finally {
        Pop-Location
    }
    Add-StepResult -Name '3/8 vitest statusBarCost' -Ok $vitestOk
} else {
    Add-StepResult -Name '3/8 vitest statusBarCost' -Ok $true -Detail 'overgeslagen (-SkipVitest)'
}

# --- 4 Pytest E2E module + gerelateerde unit tests ---
$pytestArgs = @(
    '-m', 'pytest',
    (Join-Path $RepoRoot 'tests/windows/test_status_bar_cost_e2e.py'),
    (Join-Path $RepoRoot 'tests/windows/test_team_display_defaults.py'),
    (Join-Path $RepoRoot 'tests/windows/test_apply_team_display_root.py'),
    (Join-Path $RepoRoot 'tests/test_tui_gateway_server.py::test_config_get_cost_survives_non_dict_display'),
    (Join-Path $RepoRoot 'tests/test_tui_gateway_server.py::test_config_set_cost_survives_non_dict_display'),
    (Join-Path $RepoRoot 'tests/test_tui_gateway_server.py::test_config_set_cost_toggle_empty_value'),
    '-q',
    '-o', 'addopts='
)
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $python @pytestArgs *>&1 | Out-Host
$pytestOk = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $prevEap
Add-StepResult -Name '4/8 pytest status-bar cost keten' -Ok $pytestOk -Detail $python

# --- 5 Runtime root show_cost ---
$rootCfg = Join-Path $hermesRoot 'config.yaml'
$rootOk = $false
if (Test-Path -LiteralPath $rootCfg) {
    $rootText = Get-Content -LiteralPath $rootCfg -Raw -Encoding UTF8
    $rootOk = ($rootText -match 'show_cost:\s*true')
}
Add-StepResult -Name '5/8 runtime root show_cost' -Ok $rootOk -Detail $rootCfg

# --- 6 Runtime alle profielen show_cost ---
$profilesDir = Join-Path $hermesRoot 'profiles'
$profFailures = [System.Collections.Generic.List[string]]::new()
$profCount = 0
if (Test-Path -LiteralPath $profilesDir) {
    Get-ChildItem -LiteralPath $profilesDir -Directory | Sort-Object Name | ForEach-Object {
        $profCount++
        $cfgPath = Join-Path $_.FullName 'config.yaml'
        if (-not (Test-Path -LiteralPath $cfgPath)) {
            $profFailures.Add("$($_.Name): geen config.yaml")
            return
        }
        $cfgText = Get-Content -LiteralPath $cfgPath -Raw -Encoding UTF8
        if ($cfgText -notmatch 'show_cost:\s*true') {
            $profFailures.Add("$($_.Name): show_cost ontbreekt of false")
        }
    }
} else {
    $profFailures.Add('geen profiles-map')
}
$profOk = ($profFailures.Count -eq 0) -and ($profCount -gt 0)
$profDetail = if ($profOk) { "$profCount profielen" } else { ($profFailures -join '; ') }
Add-StepResult -Name '6/8 runtime profielen show_cost' -Ok $profOk -Detail $profDetail

# --- 7 Gateway usage smoke (repo script) ---
$smokePy = Join-Path $RepoRoot 'scripts/status_bar_cost_gateway_smoke.py'
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $python $smokePy *>&1 | Out-Host
$gatewayOk = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $prevEap
Add-StepResult -Name '7/8 gateway _get_usage cost_usd smoke' -Ok $gatewayOk -Detail 'scripts/status_bar_cost_gateway_smoke.py'

# --- 8 README /cost documented ---
$readme = Join-Path $RepoRoot 'ui-tui/README.md'
$readmeOk = $false
if (Test-Path -LiteralPath $readme) {
    $readmeText = Get-Content -LiteralPath $readme -Raw -Encoding UTF8
    $readmeOk = ($readmeText -match '/cost')
}
Add-StepResult -Name '8/8 ui-tui README /cost' -Ok $readmeOk

# --- Rapport ---
$reportPath = Join-Path $scriptRoot ("STATUS_BAR_COST_E2E_REPORT_$reportStamp.md")
$status = if ($failures -eq 0) { 'PASS' } else { 'FAIL' }
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Status Bar Cost E2E - $status")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$sb.AppendLine("Hermes root: ``$hermesRoot``")
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
    [void]$sb.AppendLine("**$failures** stap(pen) gefaald. Herstel: ``windows\APPLY_TEAM_DISPLAY.bat``, daarna audit opnieuw.")
} else {
    [void]$sb.AppendLine('Alle stappen geslaagd. Start Hermes opnieuw of `/new` om statusbalk-kosten te zien.')
}
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host ''
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== STATUS BAR COST E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== STATUS BAR COST E2E: PASS ===' -ForegroundColor Green
exit 0
