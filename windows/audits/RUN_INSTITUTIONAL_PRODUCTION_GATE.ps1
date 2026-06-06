# Gecombineerde institutioneel productie-poort: Python + KnowledgeRepository + platform hardening
# + repo-hygiene hardening (audits/RUN_INSTITUTIONAL_HARDENING_E2E.bat, 14/14) + python wiring.
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest,
    [switch]$IncludeMemoryGate
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

. (Join-Path $scriptRoot '..\HermesShellCommon.ps1')
Clear-HermesPytestAddoptsForAudit

$failures = 0
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
Write-Host '=== Institutional Production Gate ===' -ForegroundColor Cyan

$steps = @(
    @{ Name = 'RUN_HERMES_PYTHON_INSTITUTIONAL_E2E'; Script = 'RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.ps1' },
    @{ Name = 'RUN_KNOWLEDGE_REPOSITORY_E2E'; Script = 'RUN_KNOWLEDGE_REPOSITORY_E2E.ps1' },
    @{ Name = 'RUN_PLATFORM_HARDENING_PRODUCTION_GATE'; Script = 'RUN_PLATFORM_HARDENING_PRODUCTION_GATE.ps1' }
)
# Repo-hygiene + legal skills (audits/ — geen netwerk)
$repoHardeningBat = Join-Path $RepoRoot 'audits\RUN_INSTITUTIONAL_HARDENING_E2E.bat'
if ($IncludeMemoryGate) {
    $steps += @{ Name = 'RUN_MEMORY_PRODUCTION_GATE'; Script = 'RUN_MEMORY_PRODUCTION_GATE.ps1' }
}

$results = [System.Collections.Generic.List[object]]::new()
foreach ($step in $steps) {
    $path = Join-Path $scriptRoot $step.Script
    Write-Host ('--- ' + $step.Name + ' ---') -ForegroundColor Cyan
    $ok = $true
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host ('[FAIL] ontbreekt: ' + $path) -ForegroundColor Red
        $ok = $false
    } else {
        if ($SkipPytest -and $step.Script -ne 'RUN_MEMORY_PRODUCTION_GATE.ps1') {
            & $path -RepoRoot $RepoRoot -SkipPytest
        } else {
            & $path -RepoRoot $RepoRoot
        }
        if ($LASTEXITCODE -ne 0) { $ok = $false }
    }
    if (-not $ok) { $failures++ }
    $results.Add([pscustomobject]@{ Step = $step.Name; Ok = $ok })
}

Write-Host '--- RUN_INSTITUTIONAL_HARDENING_E2E ---' -ForegroundColor Cyan
$hardeningOk = $false
if (-not (Test-Path -LiteralPath $repoHardeningBat)) {
    Write-Host ('[FAIL] ontbreekt: ' + $repoHardeningBat) -ForegroundColor Red
} else {
    cmd /c "`"$repoHardeningBat`""
    if ($LASTEXITCODE -eq 0) { $hardeningOk = $true }
    else { Write-Host ('[FAIL] RUN_INSTITUTIONAL_HARDENING_E2E exit ' + $LASTEXITCODE) -ForegroundColor Red }
}
if (-not $hardeningOk) { $failures++ }
$results.Add([pscustomobject]@{ Step = 'RUN_INSTITUTIONAL_HARDENING_E2E'; Ok = $hardeningOk })

$wiring = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/validate_windows_python_wiring.ps1'
Write-Host '--- validate_windows_python_wiring ---' -ForegroundColor Cyan
$wiringOk = $false
if (Test-Path -LiteralPath $wiring) {
    & $wiring -RepoRoot $RepoRoot
    $wiringOk = ($LASTEXITCODE -eq 0)
} else {
    Write-Host '[FAIL] validate_windows_python_wiring.ps1 ontbreekt' -ForegroundColor Red
}
if (-not $wiringOk) { $failures++ }
$results.Add([pscustomobject]@{ Step = 'validate_windows_python_wiring'; Ok = $wiringOk })

$status = if ($failures -eq 0) { 'PASS' } else { "FAIL ($failures)" }
$reportPath = Join-Path $scriptRoot ('INSTITUTIONAL_PRODUCTION_GATE_REPORT_' + $reportStamp + '.md')
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Institutional Production Gate - $status")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$sb.AppendLine("Repo: $RepoRoot")
[void]$sb.AppendLine('')
foreach ($r in $results) {
    $mark = if ($r.Ok) { 'PASS' } else { 'FAIL' }
    [void]$sb.AppendLine("- $($r.Step): $mark")
}
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== INSTITUTIONAL PRODUCTION GATE: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== INSTITUTIONAL PRODUCTION GATE: PASS ===' -ForegroundColor Green
exit 0
