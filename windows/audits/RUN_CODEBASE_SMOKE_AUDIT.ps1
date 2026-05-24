# Codebase smoke audit (E1/E2 subset) — niet gelijk aan release-gate (E3).
# Rapport: windows/audits/CODEBASE_SMOKE_AUDIT_REPORT_<timestamp>.md
param(
    [string]$RepoRoot = '',
    [string]$ReportPath = '',
    [string]$ReportStamp = '',
    [switch]$IncludePygount,
    [switch]$SkipPygount,
    [switch]$IncludeTuiGatewayPytest,
    [switch]$IncludeParetoE2E,
    [switch]$FullSmoke,
    [switch]$IncludeReleaseGate
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}
Set-Location -LiteralPath $RepoRoot

if ($FullSmoke) {
    $IncludePygount = $true
    $IncludeTuiGatewayPytest = $true
    $IncludeParetoE2E = $true
}
if (-not $SkipPygount -and -not $PSBoundParameters.ContainsKey('IncludePygount')) {
    # default: geen pygount (snel)
}

$failures = 0
$stepLog = [ordered]@{
    started          = (Get-Date -Format 'o')
    repo             = $RepoRoot
    release_gate_run = $IncludeReleaseGate.IsPresent
    flags            = @{
        IncludePygount            = $IncludePygount.IsPresent
        IncludeTuiGatewayPytest = $IncludeTuiGatewayPytest.IsPresent
        IncludeParetoE2E        = $IncludeParetoE2E.IsPresent
        FullSmoke                 = $FullSmoke.IsPresent
    }
    warnings = [System.Collections.Generic.List[string]]::new()
    pygount  = $null
    steps    = [System.Collections.Generic.List[object]]::new()
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
    return 'python'
}

function Add-StepLog {
    param(
        [string]$Name,
        [string]$Tier,
        [string]$Source,
        [int]$Exit,
        [string]$Detail = '',
        [switch]$Skipped,
        [switch]$Optional
    )
    $script:stepLog.steps.Add([ordered]@{
            timestamp = (Get-Date -Format 'HH:mm:ss')
            name      = $Name
            tier      = $Tier
            source    = $Source
            exit      = $Exit
            detail    = $Detail
            skipped   = [bool]$Skipped
            optional  = [bool]$Optional
        })
    if (-not $Skipped -and -not $Optional -and $Exit -ne 0) {
        $script:failures++
    }
}

function Invoke-SmokeStep {
    param(
        [string]$Name,
        [string]$Tier,
        [string]$Source,
        [scriptblock]$Action,
        [switch]$AllowSkip,
        [switch]$Optional
    )
    Write-Host ""
    Write-Host "=== $Name [$Tier] ===" -ForegroundColor Cyan
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $exit = 0
    $detail = ''
    $skipped = $false
    try {
        & $Action
        $exit = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
        if ($exit -eq 0) {
            Write-Host ('[OK] ' + $Name) -ForegroundColor Green
        } elseif ($AllowSkip -and $exit -eq 2) {
            Write-Host ('[SKIP] ' + $Name) -ForegroundColor Yellow
            $skipped = $true
            $exit = 0
        } else {
            Write-Host ('[FAIL] ' + $Name + ' (exit ' + $exit + ')') -ForegroundColor Red
        }
    } catch {
        $exit = 1
        $detail = $_.Exception.Message
        Write-Host ('[FAIL] ' + $Name + ' (' + $detail + ')') -ForegroundColor Red
    }
    $sw.Stop()
    if (-not $detail) { $detail = "exit $exit ($($sw.ElapsedMilliseconds)ms)" }
    Add-StepLog -Name $Name -Tier $Tier -Source $Source -Exit $exit -Detail $detail -Skipped:$skipped -Optional:$Optional
}

$py = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot
$env:OPENROUTER_API_KEY = ''
$env:OPENAI_API_KEY = ''
$env:NOUS_API_KEY = ''

Write-Host '=== CODEBASE SMOKE AUDIT (E1/E2) ===' -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"
Write-Host "Python: $py"

Invoke-SmokeStep -Name 'pytest_windows_critical' -Tier 'E2' -Source 'tests/windows/test_critical_windows_scripts.py' {
    & $py -m pytest tests/windows/test_critical_windows_scripts.py -q --tb=short
    $global:LASTEXITCODE = $LASTEXITCODE
}

Invoke-SmokeStep -Name 'verify_windows_chain' -Tier 'E1' -Source 'windows/verify_windows_script_chain.ps1' -AllowSkip {
    $chain = Join-Path $RepoRoot 'windows/verify_windows_script_chain.ps1'
    if (-not (Test-Path -LiteralPath $chain)) {
        $global:LASTEXITCODE = 2
        return
    }
    & $chain
    $global:LASTEXITCODE = $LASTEXITCODE
}

Invoke-SmokeStep -Name 'diagnose_renderer' -Tier 'E1' -Source 'scripts/diagnose_renderer.py' {
    & $py (Join-Path $RepoRoot 'scripts/diagnose_renderer.py') --verify
    $global:LASTEXITCODE = $LASTEXITCODE
}

Invoke-SmokeStep -Name 'audit_skill_drift' -Tier 'E1' -Source 'scripts/audit_skill_drift.py' {
    & $py (Join-Path $RepoRoot 'scripts/audit_skill_drift.py')
    $global:LASTEXITCODE = $LASTEXITCODE
}

Invoke-SmokeStep -Name 'verify_usage_cost_bar' -Tier 'E1' -Source 'scripts/verify_usage_cost_bar.py' {
    & $py (Join-Path $RepoRoot 'scripts/verify_usage_cost_bar.py') --verify
    $global:LASTEXITCODE = $LASTEXITCODE
}

Invoke-SmokeStep -Name 'verify_pareto_router' -Tier 'E1' -Source 'scripts/verify_pareto_router.py' {
    & $py (Join-Path $RepoRoot 'scripts/verify_pareto_router.py') --verify
    $global:LASTEXITCODE = $LASTEXITCODE
}

Invoke-SmokeStep -Name 'pytest_profile_inheritance' -Tier 'E2' -Source 'tests/hermes_cli/test_profile_model_inheritance.py' {
    & $py -m pytest tests/hermes_cli/test_profile_model_inheritance.py -q --tb=short
    $global:LASTEXITCODE = $LASTEXITCODE
}

Invoke-SmokeStep -Name 'pytest_sessiondb' -Tier 'E2' -Source 'tests/test_hermes_state.py' {
    & $py -m pytest tests/test_hermes_state.py -q --tb=short
    $global:LASTEXITCODE = $LASTEXITCODE
}

Invoke-SmokeStep -Name 'pytest_sessiondb_wal' -Tier 'E2' -Source 'tests/test_hermes_state_wal_fallback.py' {
    & $py -m pytest tests/test_hermes_state_wal_fallback.py -q --tb=short
    $global:LASTEXITCODE = $LASTEXITCODE
}

if ($IncludeTuiGatewayPytest) {
    Invoke-SmokeStep -Name 'pytest_tui_gateway_full' -Tier 'E2' -Source 'tests/test_tui_gateway_server.py' {
        & $py -m pytest tests/test_tui_gateway_server.py -q --tb=short
        $global:LASTEXITCODE = $LASTEXITCODE
    }
} else {
    Invoke-SmokeStep -Name 'tui_gateway_collect_only' -Tier 'E2' -Source 'tests/test_tui_gateway_server.py' {
        $out = & $py -m pytest tests/test_tui_gateway_server.py --collect-only -q 2>&1
        $global:LASTEXITCODE = $LASTEXITCODE
        $count = ($out | Where-Object { $_ -match '::test_' }).Count
        if ($count -eq 0 -and "$out" -match '(\d+)\s+test') {
            $count = [int]$Matches[1]
        }
        Write-Host "Collect-only: $count tests in test_tui_gateway_server.py"
        $script:stepLog.steps[-1].detail = "collect-only: $count tests (niet uitgevoerd)"
    }
}

if ($IncludeParetoE2E) {
    Invoke-SmokeStep -Name 'pareto_e2e' -Tier 'E2' -Source 'windows/audits/RUN_PARETO_E2E.ps1' -Optional {
        & (Join-Path $scriptRoot 'RUN_PARETO_E2E.ps1') -RepoRoot $RepoRoot
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

if ($IncludePygount) {
    Invoke-SmokeStep -Name 'pygount_snapshot' -Tier 'E1' -Source 'pygount' -AllowSkip -Optional {
        $pg = Get-Command pygount -ErrorAction SilentlyContinue
        if (-not $pg) {
            Write-Host 'SKIP: pygount niet op PATH' -ForegroundColor Yellow
            $global:LASTEXITCODE = 2
            return
        }
        $summary = & pygount --format=summary . 2>&1
        $global:LASTEXITCODE = $LASTEXITCODE
        $code = ($summary | Select-String -Pattern '^\s*code\s+(\d+)' | ForEach-Object { $_.Matches[0].Groups[1].Value }) | Select-Object -First 1
        $comment = ($summary | Select-String -Pattern 'comment\s+(\d+)' | ForEach-Object { $_.Matches[0].Groups[1].Value }) | Select-Object -First 1
        $script:stepLog.pygount = @{
            date    = (Get-Date -Format 'yyyy-MM-dd')
            code    = $code
            comment = $comment
        }
        Write-Host $summary
    }
}

if ($IncludeReleaseGate) {
    $stepLog.warnings.Add('Release-gate gevraagd maar niet automatisch uitgevoerd in smoke — gebruik RUN_AUDITS -IncludeAllE2E of RUN_PYTEST.ps1')
}

if ($ReportStamp) {
    $stamp = $ReportStamp
} else {
    $stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
}
$jsonPath = Join-Path $scriptRoot "CODEBASE_SMOKE_STEPLOG_$stamp.json"
if ($ReportPath) {
    $reportPath = $ReportPath
} else {
    $reportPath = Join-Path $scriptRoot "CODEBASE_SMOKE_AUDIT_REPORT_$stamp.md"
}

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($jsonPath, ($stepLog | ConvertTo-Json -Depth 6), $utf8NoBom)

$emit = Join-Path $RepoRoot 'scripts/emit_codebase_smoke_report.py'
if (Test-Path -LiteralPath $emit) {
    & $py $emit $jsonPath -o $reportPath
    if ($LASTEXITCODE -ne 0) {
        $failures++
    }
} else {
    $stepLog.warnings.Add('emit_codebase_smoke_report.py ontbreekt')
    $failures++
}

Write-Host ""
Write-Host "Staplog: $jsonPath"
Write-Host "Rapport: $reportPath"
if ($failures -gt 0) {
    Write-Host "CODEBASE_SMOKE_AUDIT: $failures stap(pen) gefaald." -ForegroundColor Red
    exit 1
}
Write-Host 'CODEBASE_SMOKE_AUDIT: PASS (smoke - geen E3 release-gate).' -ForegroundColor Green
exit 0
