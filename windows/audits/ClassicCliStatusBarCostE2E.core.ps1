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
    'hermes_cli/status_bar_cost.py',
    'hermes_cli/usage_snapshot.py',
    'hermes_cli/commands.py',
    'cli.py',
    'tests/hermes_cli/test_status_bar_cost.py',
    'tests/cli/test_cli_status_bar.py',
    'scripts/status_bar_cost_classic_cli_smoke.py',
    'scripts/status_bar_cost_classic_cli_live_smoke.py',
    'scripts/verify_usage_cost_bar.py',
    'windows/audits/RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1',
    'windows/audits/ClassicCliStatusBarCostE2E.core.ps1'
)
$repoOk = $true
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot ($rel -replace '/', '\')))) {
        $repoOk = $false
        break
    }
}
Add-StepResult -Name '1/11 repo classic CLI cost artefacten' -Ok $repoOk

# --- 2 cli.py + formatter hooks ---
$cliText = Get-Content -LiteralPath (Join-Path $RepoRoot 'cli.py') -Raw -Encoding UTF8
$sbcText = Get-Content -LiteralPath (Join-Path $RepoRoot 'hermes_cli/status_bar_cost.py') -Raw -Encoding UTF8
$hooksOk = $cliText.Contains('_append_status_bar_cost_fragments') -and
    $cliText.Contains('_handle_cost_command') -and
    ($cliText -match 'canonical == .cost.') -and
    $cliText.Contains('_show_cost') -and
    $sbcText.Contains('format_status_bar_cost_rich') -and
    $sbcText.Contains('resolve_status_bar_cost_label')
Add-StepResult -Name '2/11 cli.py hooks + status_bar_cost.py' -Ok $hooksOk

# --- 3 commands.py + merge keepOurs ---
$commandsText = Get-Content -LiteralPath (Join-Path $RepoRoot 'hermes_cli/commands.py') -Raw -Encoding UTF8
$mergePs1 = Get-Content -LiteralPath (Join-Path $RepoRoot 'windows/merge_upstream_fork.ps1') -Raw -Encoding UTF8
$registryOk = $commandsText.Contains('CommandDef') -and
    $commandsText.Contains('"cost"') -and
    $mergePs1.Contains('hermes_cli/status_bar_cost.py') -and
    $mergePs1.Contains('test_status_bar_cost.py')
Add-StepResult -Name '3/11 cost command + merge keepOurs' -Ok $registryOk

# --- 4 UPSTREAM_SYNC classic parity ---
$upstreamMd = Get-Content -LiteralPath (Join-Path $RepoRoot "windows/UPSTREAM_SYNC.md") -Raw -Encoding UTF8
$upstreamOk = $upstreamMd.Contains('Classic CLI parity') -and
    $upstreamMd.Contains('status_bar_cost.py') -and
    $upstreamMd.Contains('cli.py')
Add-StepResult -Name '4/11 UPSTREAM_SYNC classic parity' -Ok $upstreamOk

# --- 5-7 Pytest keten ---
if ($SkipPytest) {
    Add-StepResult -Name '5/11 pytest status_bar_cost formatter' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
    Add-StepResult -Name '6/11 pytest cli status bar + cost' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
    Add-StepResult -Name '7/11 pytest repo e2e module' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $fmtOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-Path $RepoRoot 'tests/hermes_cli/test_status_bar_cost.py'),
        '-q', '-o', 'addopts='
    )
    Add-StepResult -Name '5/11 pytest status_bar_cost formatter' -Ok $fmtOk -Detail $python

    $cliBarOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-Path $RepoRoot 'tests/cli/test_cli_status_bar.py'),
        '-q', '-o', 'addopts='
    )
    Add-StepResult -Name '6/11 pytest cli status bar + cost' -Ok $cliBarOk

    $repoE2eOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-Path $RepoRoot 'tests/windows/test_status_bar_cost_e2e.py'),
        '-q', '-o', 'addopts='
    )
    Add-StepResult -Name '7/11 pytest repo e2e module' -Ok $repoE2eOk
}

# --- 8 Classic CLI smoke ---
$smokePy = Join-Path $RepoRoot 'scripts/status_bar_cost_classic_cli_smoke.py'
$smokeOk = Invoke-AuditCommand -Exe $python -ArgumentList @($smokePy)
Add-StepResult -Name '8/11 classic CLI smoke render + cost' -Ok $smokeOk -Detail 'status_bar_cost_classic_cli_smoke.py'

# --- 9 Live post-turn smoke (hermes chat code path) ---
$liveSmokePy = Join-Path $RepoRoot 'scripts/status_bar_cost_classic_cli_live_smoke.py'
$liveOk = Invoke-AuditCommand -Exe $python -ArgumentList @($liveSmokePy)
Add-StepResult -Name '9/11 live post-turn status bar + cost toggle' -Ok $liveOk -Detail 'status_bar_cost_classic_cli_live_smoke.py'

# --- 10 verify wiring ---
$verifyPy = Join-Path $RepoRoot 'scripts/verify_usage_cost_bar.py'
$verifyOk = Invoke-AuditCommand -Exe $python -ArgumentList @($verifyPy, '--verify')
Add-StepResult -Name '10/11 verify_usage_cost_bar classic hooks' -Ok $verifyOk

# --- 11 Documentatie ---
$cliMd = Get-Content -LiteralPath (Join-Path $RepoRoot "website/docs/user-guide/cli.md") -Raw -Encoding UTF8
$termMd = Get-Content -LiteralPath (Join-Path $RepoRoot "windows/TERMINAL_WINDOWS.md") -Raw -Encoding UTF8
$configMd = Get-Content -LiteralPath (Join-Path $RepoRoot "website/docs/user-guide/configuration.md") -Raw -Encoding UTF8
$configPy = Get-Content -LiteralPath (Join-Path $RepoRoot 'hermes_cli/config.py') -Raw -Encoding UTF8
$docsOk = $cliMd.Contains('/cost') -and
    $termMd.Contains('klassieke CLI') -and
    $configMd.Contains('classic CLI') -and
    $configPy.Contains('classic CLI status bar')
Add-StepResult -Name '11/11 docs TUI + classic CLI parity' -Ok $docsOk

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
