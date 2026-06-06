# Codebase smoke E2E — repo guardrails + RUN_CODEBASE_SMOKE_AUDIT (E1/E2, geen E3).
# Syntax-check: windows/tests/Validate-AuditPs1Syntax.ps1
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest,
    [switch]$IncludePygount,
    [switch]$IncludeTuiGatewayPytest,
    [switch]$FullSmoke
)

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}
Set-Location -LiteralPath $RepoRoot

$failures = 0
$steps = [System.Collections.Generic.List[object]]::new()
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'

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

Write-Host '=== Codebase Smoke E2E (E1/E2) ===' -ForegroundColor Cyan
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

# --- 1 Repo artefacten ---
$repoFiles = @(
    'docs/CODEBASE_AUDIT_EVIDENCE.md',
    'docs/templates/CODEBASE_AUDIT_REPORT.md',
    'docs/templates/CODEBASE_AUDIT_SMOKE_PROMPT.md',
    'docs/templates/SOUL_SHARED_CODEBASE_AUDIT.md',
    'scripts/emit_codebase_smoke_report.py',
    'windows/audits/RUN_CODEBASE_SMOKE_AUDIT.ps1',
    'windows/audits/RUN_CODEBASE_SMOKE_E2E.ps1',
    'windows/scripts/Invoke-PostSyncCodebaseSmoke.ps1',
    'windows/scripts/Invoke-UpstreamPostMerge.ps1',
    'windows/scripts/sync_soul_codebase_audit_snippet.ps1',
    'tests/windows/test_codebase_smoke_audit.py'
)
$repoOk = $true
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $repoOk = $false
        Write-Host ('  ontbreekt: ' + $rel) -ForegroundColor Red
    }
}
Add-StepResult -Name '1/5 repo codebase-audit files' -Ok $repoOk

# --- 2 Template denylist (strict) ---
$validateScript = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/validate_soul_anatomy.py'
$reportTpl = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/templates/CODEBASE_AUDIT_REPORT.md'
$tplOk = $false
if ((Test-Path -LiteralPath $validateScript) -and (Test-Path -LiteralPath $reportTpl)) {
    $tplOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        $validateScript,
        $reportTpl,
        '--check-codebase-audit-claims',
        '--strict-codebase-audit-claims'
    )
}
Add-StepResult -Name '2/5 CODEBASE_AUDIT_REPORT strict governance' -Ok $tplOk

# --- 3 Pytest wiring ---
$pytestOk = $true
if (-not $SkipPytest) {
    Clear-HermesPytestAddoptsForAudit
    $pytestArgs = @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/windows/test_codebase_smoke_audit.py'),
        '-q',
        '--tb=short'
    ) + (Get-HermesAuditPytestOverrideArgs)
    $pytestOk = Invoke-AuditCommand -Exe $python -ArgumentList $pytestArgs
} else {
    Write-Host '[SKIP] pytest test_codebase_smoke_audit.py' -ForegroundColor Yellow
}
Add-StepResult -Name '3/5 pytest codebase smoke wiring' -Ok $pytestOk -Detail $(if ($SkipPytest) { 'skipped' } else { '' })

# --- 4 Smoke audit (E1/E2 subset) ---
$smokeScript = Join-Path $scriptRoot 'RUN_CODEBASE_SMOKE_AUDIT.ps1'
$smokeArgs = @{ RepoRoot = $RepoRoot; ReportStamp = $reportStamp }
if ($IncludePygount) { $smokeArgs['IncludePygount'] = $true }
if ($IncludeTuiGatewayPytest) { $smokeArgs['IncludeTuiGatewayPytest'] = $true }
if ($FullSmoke) { $smokeArgs['FullSmoke'] = $true }
$instReportPath = Join-Path $scriptRoot ('CODEBASE_SMOKE_AUDIT_REPORT_' + $reportStamp + '.md')
$smokeArgs['ReportPath'] = $instReportPath

$smokeOk = $false
$smokeDetail = ''
if (Test-Path -LiteralPath $smokeScript) {
    & $smokeScript @smokeArgs
    $smokeOk = ($LASTEXITCODE -eq 0)
    if (Test-Path -LiteralPath $instReportPath) {
        $smokeDetail = 'institutional: ' + (Split-Path -Leaf $instReportPath)
    } else {
        $smokeDetail = 'exit ' + $LASTEXITCODE
    }
} else {
    $smokeDetail = 'RUN_CODEBASE_SMOKE_AUDIT.ps1 ontbreekt'
}
Add-StepResult -Name '4/5 RUN_CODEBASE_SMOKE_AUDIT (E1/E2)' -Ok $smokeOk -Detail $smokeDetail

# --- 5 Institutional report sanity ---
$reportOk = $false
$reportDetail = 'geen rapport'
if (Test-Path -LiteralPath $instReportPath) {
    $raw = Get-Content -LiteralPath $instReportPath -Raw -Encoding UTF8
    $reportOk = (
        ($raw -match 'Release-gate in deze run:') -and
        ($raw -match '\[E2\]') -and
        ($raw -match 'geen E3|Nee')
    )
    $reportDetail = if ($reportOk) { 'institutional report OK' } else { 'rapport mist E-tier/release-gate markers' }
}
Add-StepResult -Name '5/5 institutional smoke report' -Ok $reportOk -Detail $reportDetail

# --- E2E rapport (Pareto-stijl) ---
$e2eReport = Join-Path $scriptRoot ('CODEBASE_SMOKE_E2E_REPORT_' + $reportStamp + '.md')
$status = if ($failures -eq 0) { 'PASS' } else { 'FAIL' }
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Codebase Smoke E2E - $status")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$sb.AppendLine("Repo: ``$RepoRoot``")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('**Niveau:** E1/E2 smoke - geen E3 release-gate. Zie `docs/CODEBASE_AUDIT_EVIDENCE.md`.')
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
    [void]$sb.AppendLine("**$failures** stap(pen) gefaald. Geen release-ready classificatie.")
} else {
    [void]$sb.AppendLine('Smoke E2E geslaagd. Voor release: `RUN_PYTEST.ps1` of `RUN_AUDITS.bat -IncludeAllE2E`.')
}
if (Test-Path -LiteralPath $instReportPath) {
    [void]$sb.AppendLine('')
    $instRel = $instReportPath.Replace('\', '/')
    [void]$sb.AppendLine('Institutioneel rapport: `' + $instRel + '`')
}
$sb.ToString() | Set-Content -LiteralPath $e2eReport -Encoding UTF8
Write-Host ''
Write-Host "E2E rapport: $e2eReport" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== CODEBASE SMOKE E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== CODEBASE SMOKE E2E: PASS ===' -ForegroundColor Green
exit 0
