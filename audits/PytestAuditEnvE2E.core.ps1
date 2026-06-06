# Pytest audit-env E2E — dunne launcher (institutional gate pytest wiring).
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

$harness = Join-Path $scriptRoot 'PytestAuditEnvE2E.harness.py'
if (-not (Test-Path -LiteralPath $harness)) {
    Write-Host '[FAIL] PytestAuditEnvE2E.harness.py ontbreekt' -ForegroundColor Red
    exit 1
}

$python = Get-HermesAuditPythonLocal
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$reportPath = Join-Path $scriptRoot ("PYTEST_AUDIT_ENV_E2E_REPORT_" + $reportStamp + '.md')
$logPath = Join-Path $scriptRoot ("PYTEST_AUDIT_ENV_E2E_LOG_" + $reportStamp + '.txt')

Write-Host "=== Pytest Audit Env E2E (python: $python) ===" -ForegroundColor Cyan
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
    Write-Host '=== PYTEST AUDIT ENV E2E: FAIL ===' -ForegroundColor Red
    exit $exitCode
}

@"
# Pytest Audit Env E2E — PASS

Generated: $reportStamp
Repo: $RepoRoot
Python: $python
Log: $logPath
"@ | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host '=== PYTEST AUDIT ENV E2E: PASS ===' -ForegroundColor Green
Write-Host "Report: $reportPath"
exit 0
