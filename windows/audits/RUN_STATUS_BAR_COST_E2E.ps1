# Rich status-bar cost E2E (show_cost + cost_bar_mode + breakdown + TUI wiring).
# Syntax-check: windows/tests/Validate-AuditPs1Syntax.ps1
param(
    [string]$RepoRoot = '',
    [switch]$SkipVitest,
    [switch]$SkipRuntime,
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

function Get-PytestNodePath {
    param(
        [string]$RelativeFile,
        [string]$NodeName
    )
    $filePath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $RelativeFile
    return ($filePath + '::' + $NodeName)
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

Write-Host '=== Status Bar Cost E2E (rich) ===' -ForegroundColor Cyan
$hermesRoot = Get-HermesRoot
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

if ($ApplyDisplayFix) {
    Write-Host '--- apply_team_display (optioneel) ---' -ForegroundColor Cyan
    & (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/apply_team_display.ps1')
    Add-StepResult -Name '0/10 apply_team_display' -Ok (-not (Test-NativeCommandFailed))
}

# --- 1 Repo defaults + fork-owned artefacten ---
$defaultsPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/team_display.defaults'
$defaultsText = if (Test-Path -LiteralPath $defaultsPath) {
    Get-Content -LiteralPath $defaultsPath -Raw -Encoding UTF8
} else { '' }
$repoOk = ($defaultsText -match 'show_cost=true') -and ($defaultsText -match 'cost_bar_mode=rich')
$repoFiles = @(
    'overlay/hermes_cli/usage_snapshot.py',
    'overlay/hermes_cli/status_bar_cost.py',
    'overlay/ui-tui/src/domain/usageCostBar.ts',
    'overlay/tui_gateway/gateway_config_fork_patch.py',
    'ui-tui/src/domain/usage.ts',
    'ui-tui/src/app/createGatewayEventHandler.ts',
    'tui_gateway/server.py',
    'scripts/status_bar_cost_gateway_smoke.py',
    'scripts/verify_usage_cost_bar.py',
    'windows/audits/RUN_STATUS_BAR_COST_E2E.ps1'
)
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $repoOk = $false
        break
    }
}
Add-StepResult -Name '1/10 repo defaults + artefacten' -Ok $repoOk -Detail 'show_cost + cost_bar_mode=rich'

# --- 2 Guardrails (institutional + diagnose + verify) ---
$instE2e = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/audits/RUN_INSTITUTIONAL_E2E.ps1')
$diagPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/scripts/diagnose_renderer.py')
$mergePs1 = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/merge_upstream_fork.ps1')
$bootstrapPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/bootstrap.py')
$guardOk = ($instE2e -match 'cost_bar_mode=rich') -and ($diagPy -match 'cost_bar_mode') -and ($bootstrapPy -match 'gateway_config_fork_patch') -and ($bootstrapPy -match 'usage_snapshot')
Add-StepResult -Name '2/10 drift guards + keepOurs' -Ok $guardOk

# --- 3 Vitest (formatter + event handler turn/tools) ---
if (-not $SkipVitest) {
    Push-Location (Join-Path $RepoRoot 'ui-tui')
    try {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        & npx vitest run statusBarCost usageCostBar createGatewayEventHandler 2>&1 | Out-Host
        $vitestOk = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $prevEap
    } finally {
        Pop-Location
    }
    Add-StepResult -Name '3/10 vitest cost bar + turn delta' -Ok $vitestOk
} else {
    Add-StepResult -Name '3/10 vitest cost bar + turn delta' -Ok $true -Detail 'overgeslagen (-SkipVitest)'
}

# --- 4 Pytest keten ---
$pytestArgs = @(
    '-m', 'pytest',
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/hermes_cli/test_usage_snapshot.py'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/windows/test_status_bar_cost_e2e.py'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/windows/test_team_display_defaults.py'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/windows/test_apply_team_display_root.py'),
    (Get-PytestNodePath 'tests/test_tui_gateway_server.py' 'test_config_get_cost_survives_non_dict_display'),
    (Get-PytestNodePath 'tests/test_tui_gateway_server.py' 'test_config_set_cost_survives_non_dict_display'),
    (Get-PytestNodePath 'tests/test_tui_gateway_server.py' 'test_config_set_cost_toggle_empty_value'),
    (Get-PytestNodePath 'tests/test_tui_gateway_server.py' 'test_config_set_cost_bar_mode_rich_and_minimal'),
    (Get-PytestNodePath 'tests/test_tui_gateway_server.py' 'test_config_get_cost_bar_mode_defaults_rich'),
    '-q',
    '-o', 'addopts='
)
$pytestOk = Invoke-AuditCommand -Exe $python -ArgumentList $pytestArgs
Add-StepResult -Name '4/10 pytest snapshot + gateway config' -Ok $pytestOk -Detail $python

# --- 5 Runtime root ---
if ($SkipRuntime) {
    Add-StepResult -Name '5/10 runtime root display' -Ok $true -Detail 'overgeslagen (-SkipRuntime)'
} else {
    $rootCfg = Join-Path $hermesRoot 'config.yaml'
    $rootOk = $false
    if (Test-Path -LiteralPath $rootCfg) {
        $rootText = Get-Content -LiteralPath $rootCfg -Raw -Encoding UTF8
        $rootOk = ($rootText -match 'show_cost:\s*true') -and ($rootText -match 'cost_bar_mode:\s*rich')
    }
    Add-StepResult -Name '5/10 runtime root display' -Ok $rootOk -Detail $rootCfg
}

# --- 6 Runtime profielen ---
if ($SkipRuntime) {
    Add-StepResult -Name '6/10 runtime profielen display' -Ok $true -Detail 'overgeslagen (-SkipRuntime)'
} else {
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
            if ($cfgText -notmatch 'cost_bar_mode:\s*rich') {
                $profFailures.Add("$($_.Name): cost_bar_mode ontbreekt of niet rich")
            }
        }
    } else {
        $profFailures.Add('geen profiles-map')
    }
    $profOk = ($profFailures.Count -eq 0) -and ($profCount -gt 0)
    $profDetail = if ($profOk) { "$profCount profielen" } else { ($profFailures -join '; ') }
    Add-StepResult -Name '6/10 runtime profielen display' -Ok $profOk -Detail $profDetail
}

# --- 7 Gateway smoke (cost + breakdown) ---
$smokePy = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/status_bar_cost_gateway_smoke.py'
$gatewayOk = Invoke-AuditCommand -Exe $python -ArgumentList @($smokePy)
Add-StepResult -Name '7/10 gateway smoke cost + breakdown' -Ok $gatewayOk -Detail 'status_bar_cost_gateway_smoke.py'

# --- 8 Verify wiring script ---
$verifyPy = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/verify_usage_cost_bar.py'
$verifyOk = Invoke-AuditCommand -Exe $python -ArgumentList @($verifyPy, '--verify')
Add-StepResult -Name '8/10 verify_usage_cost_bar' -Ok $verifyOk

# --- 9 UPSTREAM_SYNC conflict-tabel ---
$upstreamMd = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/UPSTREAM_SYNC.md')
$upstreamOk = ($upstreamMd -match 'usage_snapshot.py') -and ($upstreamMd -match 'usageCostBar.ts') -and ($upstreamMd -match 'cost_bar_mode=rich')
Add-StepResult -Name '9/10 UPSTREAM_SYNC cost-bar tabel' -Ok $upstreamOk

# --- 10 Documentatie ---
$readmeOk = $false
foreach ($rel in @('windows/TERMINAL_WINDOWS.md', 'docs/NOUS_OVERLAY_ARCHITECTURE.md', 'ui-tui/README.md')) {
    $readme = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel
    if (-not (Test-Path -LiteralPath $readme)) { continue }
    $readmeText = Get-Content -LiteralPath $readme -Raw -Encoding UTF8
    if (($readmeText -match 'cost_bar_mode') -and ($readmeText -like '*cost*')) {
        $readmeOk = $true
        break
    }
}
Add-StepResult -Name '10/10 cost-bar documentatie' -Ok $readmeOk

# --- Rapport ---
$reportFileName = 'STATUS_BAR_COST_E2E_REPORT_' + $reportStamp + '.md'
$reportPath = Join-Path $scriptRoot $reportFileName
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
    [void]$sb.AppendLine("**$failures** stap(pen) gefaald. Herstel: ``windows\APPLY_TEAM_DISPLAY.bat``, audit met ApplyDisplayFix.")
} else {
    [void]$sb.AppendLine('Alle stappen geslaagd. Na wijziging env: /new in Hermes.')
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
