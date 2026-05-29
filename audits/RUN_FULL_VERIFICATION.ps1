# Volledige verificatie-matrix (geen shortcuts): default pytest + integration + e2e + rag + RUN_AUDITS.
# Logs: audits/FULL_VERIFY_*.log
param(
    [switch]$SkipRunAudits,
    [switch]$SkipParallelDefault
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot

chcp 65001 > $null
$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $utf8
[Console]::InputEncoding = $utf8
$OutputEncoding = $utf8
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

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
    if (Test-Path -LiteralPath $logPath) { Remove-Item -LiteralPath $logPath -Force }
    $code = 0
    try {
        $output = & $Action 2>&1
        if ($null -ne $output) {
            $text = if ($output -is [array]) { ($output | ForEach-Object { "$_" }) -join "`n" } else { "$output" }
            [System.IO.File]::AppendAllText($logPath, $text + "`n", $utf8)
        }
        $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
    } catch {
        [System.IO.File]::AppendAllText($logPath, $_.Exception.Message + "`n", $utf8)
        $code = 1
    }
    [System.IO.File]::AppendAllText($logPath, "EXIT:$code`n", $utf8)
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

function Invoke-PytestMarked {
    param(
        [string]$Marker,
        [string]$LogFile
    )
    $prevPytestTimeout = $env:PYTEST_TIMEOUT
    Remove-Item Env:\PYTEST_TIMEOUT -ErrorAction SilentlyContinue
    try {
        Invoke-VerifyStep "pytest-$Marker" $LogFile {
            & $py -m pytest -m $Marker -v --tb=short `
                -o "addopts=-m $Marker --timeout=600 --timeout-method=thread"
            $global:LASTEXITCODE = $LASTEXITCODE
        }
    } finally {
        if ($null -eq $prevPytestTimeout) {
            Remove-Item Env:\PYTEST_TIMEOUT -ErrorAction SilentlyContinue
        } else {
            $env:PYTEST_TIMEOUT = $prevPytestTimeout
        }
    }
}

Invoke-PytestMarked -Marker 'integration' -LogFile 'FULL_VERIFY_integration.log'
Invoke-PytestMarked -Marker 'e2e' -LogFile 'FULL_VERIFY_e2e.log'
Invoke-PytestMarked -Marker 'rag_integration' -LogFile 'FULL_VERIFY_rag_integration.log'

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
