# Volledige verificatie-matrix (geen shortcuts): default pytest + integration + e2e + rag + RUN_AUDITS.
# Logs: audits/FULL_VERIFY_*.log
param(
    [switch]$SkipRunAudits,
    [switch]$SkipParallelDefault
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot

$py = if ($env:HERMES_PYTHON) { $env:HERMES_PYTHON } else {
    Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
}
if (-not (Test-Path -LiteralPath $py)) {
    Write-Host "FAIL: Python niet gevonden: $py" -ForegroundColor Red
    exit 1
}

$failures = 0
$logDir = Join-Path $repoRoot 'audits'

function Invoke-VerifyStep {
    param(
        [string]$Name,
        [string]$LogFile,
        [scriptblock]$Action
    )
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    $logPath = Join-Path $logDir $LogFile
    try {
        & $Action 2>&1 | Tee-Object -FilePath $logPath
        $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
    } catch {
        $_ | Out-File -FilePath $logPath -Append -Encoding utf8
        $code = 1
    }
    "EXIT:$code" | Out-File -FilePath $logPath -Append -Encoding utf8
    if ($code -eq 0) {
        Write-Host "[OK] $Name" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $Name (exit $code) - zie $logPath" -ForegroundColor Red
        $script:failures++
    }
}

if (-not $SkipParallelDefault) {
    Invoke-VerifyStep 'default-pytest-parallel' 'FULL_VERIFY_default_parallel.log' {
        & $py (Join-Path $repoRoot 'scripts\run_tests_parallel.py')
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

Invoke-VerifyStep 'pytest-integration' 'FULL_VERIFY_integration.log' {
    & $py -m pytest -m integration -v --tb=short -o "addopts=--timeout=120 --timeout-method=thread"
    $global:LASTEXITCODE = $LASTEXITCODE
}

Invoke-VerifyStep 'pytest-e2e' 'FULL_VERIFY_e2e.log' {
    & $py -m pytest -m e2e -v --tb=short -o "addopts=--timeout=600 --timeout-method=thread"
    $global:LASTEXITCODE = $LASTEXITCODE
}

Invoke-VerifyStep 'pytest-rag-integration' 'FULL_VERIFY_rag_integration.log' {
    & $py -m pytest -m rag_integration -v --tb=short -o "addopts=--timeout=600 --timeout-method=thread"
    $global:LASTEXITCODE = $LASTEXITCODE
}

if (-not $SkipRunAudits) {
    Invoke-VerifyStep 'run-audits-full' 'FULL_VERIFY_RUN_AUDITS.log' {
        & (Join-Path $repoRoot 'windows\audits\RUN_AUDITS.ps1') `
            -IncludeAllE2E `
            -IncludeInstitutionalProductionGate `
            -IncludeRepoHygieneE2E `
            -IncludeUpdateHermesIntegrationE2E
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}

Write-Host ""
if ($failures -gt 0) {
    Write-Host "FULL_VERIFICATION: $failures stap(pen) gefaald." -ForegroundColor Red
    exit 1
}
Write-Host "FULL_VERIFICATION: alles geslaagd." -ForegroundColor Green
exit 0
