# Classic CLI status-bar cost E2E core (logic). Launcher: RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1
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

Write-Host '=== Classic CLI Status Bar Cost E2E ===' -ForegroundColor Cyan
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

# --- 1 Repo artefacten ---
$repoFiles = @(
    'overlay/hermes_cli/status_bar_cost.py',
    'overlay/hermes_cli/usage_snapshot.py',
    'overlay/hermes_cli/cli_fork_patch.py',
    'overlay/bootstrap.py',
    'cli.py',
    'tests/hermes_cli/test_status_bar_cost.py',
    'tests/cli/test_cli_status_bar.py',
    'scripts/status_bar_cost_classic_cli_smoke.py',
    'scripts/status_bar_cost_classic_cli_live_smoke.py',
    'scripts/verify_usage_cost_bar.py',
    'agent/usage_pricing.py',
    'windows/audits/RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1',
    'windows/audits/ClassicCliStatusBarCostE2E.core.ps1'
)
$repoOk = $true
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $repoOk = $false
        break
    }
}
Add-StepResult -Name '1/12 repo classic CLI cost artefacten' -Ok $repoOk

# --- 2 overlay cli patch + formatter ---
$patchText = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/cli_fork_patch.py')
$bootstrapText = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/bootstrap.py')
$sbcText = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/status_bar_cost.py')
$hooksOk = $patchText.Contains('_append_status_bar_cost_fragments') -and
    $patchText.Contains('apply_cli_fork_patch') -and
    $bootstrapText.Contains('apply_cli_fork_patch') -and
    $sbcText.Contains('format_status_bar_cost_rich') -and
    $sbcText.Contains('resolve_status_bar_cost_label')
Add-StepResult -Name '2/12 overlay cli patch + status_bar_cost.py' -Ok $hooksOk

# --- 3 merge keepOurs overlay paths ---
$mergePs1 = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/merge_upstream_fork.ps1')
$registryOk = ($mergePs1.Contains('overlay/hermes_cli') -or $mergePs1.Contains('status_bar_cost.py')) -and
    $mergePs1.Contains('test_status_bar_cost.py')
Add-StepResult -Name '3/12 merge keepOurs overlay/cost tests' -Ok $registryOk

# --- 4 UPSTREAM_SYNC classic parity ---
$upstreamMd = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath "windows/UPSTREAM_SYNC.md")
$upstreamOk = $upstreamMd.Contains('Classic CLI parity') -and
    $upstreamMd.Contains('status_bar_cost.py') -and
    $upstreamMd.Contains('cli.py')
Add-StepResult -Name '4/12 UPSTREAM_SYNC classic parity' -Ok $upstreamOk

# --- 5-7 Pytest keten ---
if ($SkipPytest) {
    Add-StepResult -Name '5/12 pytest status_bar_cost formatter' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
    Add-StepResult -Name '6/12 pytest cli status bar + cost' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
    Add-StepResult -Name '7/12 pytest repo e2e module' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    Clear-HermesPytestAddoptsForAudit
    $fmtOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/hermes_cli/test_status_bar_cost.py'),
        '-q'
    ) + (Get-HermesAuditPytestOverrideArgs)
    Add-StepResult -Name '5/12 pytest status_bar_cost formatter' -Ok $fmtOk -Detail $python

    $cliBarOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/cli/test_cli_status_bar.py'),
        '-q'
    ) + (Get-HermesAuditPytestOverrideArgs)
    Add-StepResult -Name '6/12 pytest cli status bar + cost' -Ok $cliBarOk

    $repoE2eOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/windows/test_status_bar_cost_e2e.py'),
        '-q'
    ) + (Get-HermesAuditPytestOverrideArgs)
    Add-StepResult -Name '7/12 pytest repo e2e module' -Ok $repoE2eOk
}

# --- 8 Classic CLI smoke ---
$smokePy = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/status_bar_cost_classic_cli_smoke.py'
$smokeOk = Invoke-AuditCommand -Exe $python -ArgumentList @($smokePy)
Add-StepResult -Name '8/12 classic CLI smoke render + cost' -Ok $smokeOk -Detail 'status_bar_cost_classic_cli_smoke.py'

# --- 9 Live post-turn smoke (hermes chat code path) ---
$liveSmokePy = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/status_bar_cost_classic_cli_live_smoke.py'
$liveOk = Invoke-AuditCommand -Exe $python -ArgumentList @($liveSmokePy)
Add-StepResult -Name '9/12 live post-turn status bar + cost toggle' -Ok $liveOk -Detail 'status_bar_cost_classic_cli_live_smoke.py'

# --- 10 verify wiring ---
$verifyPy = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/verify_usage_cost_bar.py'
$verifyOk = Invoke-AuditCommand -Exe $python -ArgumentList @($verifyPy, '--verify')
Add-StepResult -Name '10/12 verify_usage_cost_bar classic hooks' -Ok $verifyOk

# --- 11 Documentatie ---
$cliMd = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath "website/docs/user-guide/cli.md")
$termMd = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath "windows/TERMINAL_WINDOWS.md")
$configMd = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath "website/docs/user-guide/configuration.md")
$configPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'hermes_cli/config.py')
$docsOk = ($cliMd.Contains('/cost') -or $termMd.Contains('/cost')) -and
    $termMd.Contains('klassieke CLI') -and
    $configMd.Contains('show_cost') -and
    $configPy.Contains('show_cost')
Add-StepResult -Name '11/12 docs TUI + classic CLI parity' -Ok $docsOk

# --- 12 Gemini cache pricing (geen n/a bij cache hits) ---
$pricingText = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'agent/usage_pricing.py')
$snapshotText = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/usage_snapshot.py')
$catalogOk = ($pricingText.Contains('gemini') -or $pricingText.Contains('pricing')) -and
    $snapshotText.Contains('build_session_usage_snapshot')
$seedOk = $snapshotText.Contains('build_session_usage_snapshot') -or $snapshotText.Contains('_seed_agent_session_cost')
if ($SkipPytest) {
    $geminiPyOk = $true
    $geminiDetail = 'overgeslagen (-SkipPytest)'
} else {
    $geminiPricingOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/agent/test_usage_pricing.py'),
        '-q', '-o', 'addopts=',
        '-k', 'gemini_35 or gemini_31 or gemini_25_flash_cache or google_gemini_cli'
    )
    $geminiSnapshotOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/hermes_cli/test_usage_snapshot.py'),
        '-q', '-o', 'addopts=',
        '-k', 'gemini_35'
    )
    $geminiPyOk = $geminiPricingOk -and $geminiSnapshotOk
    $geminiDetail = 'usage_pricing + usage_snapshot gemini cache'
}
$geminiOk = $catalogOk -and $seedOk -and $geminiPyOk
Add-StepResult -Name '12/12 Gemini cache pricing catalog + snapshot' -Ok $geminiOk -Detail $geminiDetail

# --- Rapport ---
$reportPath = Join-Path $scriptRoot ('CLASSIC_CLI_STATUS_BAR_COST_E2E_REPORT_' + $reportStamp + ('.' + 'md'))
$status = if ($failures -eq 0) { 'PASS' } else { 'FAIL' }
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Classic CLI Status Bar Cost E2E - $status")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$sb.AppendLine(('Repo: `' + $RepoRoot + '`'))
[void]$sb.AppendLine('')
[void]$sb.AppendLine('| Stap | Status | Detail |')
[void]$sb.AppendLine('|------|--------|--------|')
foreach ($s in $steps) {
    $rowStatus = if ($s.Ok) { 'PASS' } else { 'FAIL' }
    $rowDetail = ($s.Detail -replace '\|', '/').Replace([char]13, ' ').Replace([char]10, ' ')
    [void]$sb.AppendLine(('| {0} | {1} | {2} |' -f $s.Step, $rowStatus, $rowDetail))
}
[void]$sb.AppendLine('')
if ($failures -gt 0) {
    [void]$sb.AppendLine(('**' + $failures + '** stap(pen) gefaald. Controleer pytest/smoke output hierboven.'))
} else {
    [void]$sb.AppendLine('Alle stappen geslaagd. Live post-turn smoke dekt hermes chat statusbalk en cost toggle (geen PTY nodig).')
}
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host ''
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== CLASSIC CLI STATUS BAR COST E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== CLASSIC CLI STATUS BAR COST E2E: PASS ===' -ForegroundColor Green
exit 0
