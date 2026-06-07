# Fork tests/hermes_cli/ migratie E2E — upstream-pariteit + staged guard.
param(
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

. (Join-Path $RepoRoot 'windows\HermesShellCommon.ps1')

function Get-HermesAuditPythonLocal {
    if ($env:HERMES_AUDIT_PYTHON -and (Test-Path -LiteralPath $env:HERMES_AUDIT_PYTHON)) {
        return $env:HERMES_AUDIT_PYTHON
    }
    $fallback = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if (Test-Path -LiteralPath $fallback) { return $fallback }
    return 'python'
}

$harness = Join-Path $scriptRoot 'ForkHermesCliTestMigrationE2E.harness.py'
if (-not (Test-Path -LiteralPath $harness)) {
    Write-Host '[FAIL] ForkHermesCliTestMigrationE2E.harness.py ontbreekt' -ForegroundColor Red
    exit 1
}

$python = Get-HermesAuditPythonLocal
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$reportPath = Join-Path $scriptRoot ("FORK_HERMES_CLI_TEST_MIGRATION_E2E_REPORT_" + $reportStamp + '.md')
$logPath = Join-Path $scriptRoot ("FORK_HERMES_CLI_TEST_MIGRATION_E2E_LOG_" + $reportStamp + '.txt')

Write-Host "=== Fork hermes_cli test migration E2E (python: $python) ===" -ForegroundColor Cyan
Clear-HermesPytestAddoptsForAudit
$env:PYTHONPATH = $RepoRoot

Push-Location $RepoRoot
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    & $python $harness 2>&1 | Tee-Object -FilePath $logPath
    $exitCode = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $prevEap
    Pop-Location
}

if ($exitCode -ne 0) {
    Write-Host '=== FORK HERMES CLI TEST MIGRATION E2E: FAIL ===' -ForegroundColor Red
    exit $exitCode
}

@"
# Fork hermes_cli test migration E2E — PASS

Generated: $reportStamp
Repo: $RepoRoot
Python: $python
Log: $logPath

Coverage: lege exceptions-lijst, upstream-pariteit tests/hermes_cli/, pre-merge strict,
gate manifest zonder hermes_cli paden, gemigreerde samples, staged guard mini-repo,
PowerShell hygiene wrapper.
"@ | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host '=== FORK HERMES CLI TEST MIGRATION E2E: PASS ===' -ForegroundColor Green
Write-Host "Report: $reportPath"
exit 0
