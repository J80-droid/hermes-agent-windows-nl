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
$issuesStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$issuesPath = Join-Path $env:TEMP "hermes_FULL_VERIFY_ISSUES_$issuesStamp.txt"
$script:issuesSeen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$script:stepLogFiles = [System.Collections.Generic.List[string]]::new()

function Initialize-FullVerifyIssuesFile {
    $header = @(
        "Hermes FULL_VERIFICATION issues (fails / warnings / errors)"
        "Generated: $(Get-Date -Format o)"
        "Repo: $repoRoot"
        "Issues file: $issuesPath"
        ""
        "=== Live capture (during run) ==="
        ""
    ) -join "`n"
    [System.IO.File]::WriteAllText($issuesPath, $header, $utf8)
}

function Test-FullVerifyIssueLine {
    param([string]$Line)
    if (-not $Line -or $Line.Length -lt 3) { return $false }
    if ($Line -match '^\s*STEP:|^\s*START:|^\s*END:|^\s*EXIT:0\s*$') { return $false }
    if ($Line -match '(?i)(\[FAIL\]|^\s*FAIL\b|\[WARN\]|^\s*WARN\b|\bERROR\b|FAILED\s|::\s*FAILED|AssertionError|PermissionError|Traceback\s*\(|E\s+AssertionError|pytest\.fail|Step-Fail|RUN_.*:\s*FAIL|gefaald|mislukt)') {
        return $true
    }
    if ($Line -match '^\s*EXIT:[1-9]\d*\s*$') { return $true }
    return $false
}

function Add-FullVerifyIssue {
    param(
        [string]$Source,
        [string]$Line
    )
    if (-not (Test-FullVerifyIssueLine -Line $Line)) { return }
    $key = "$Source|$Line"
    if ($script:issuesSeen.Contains($key)) { return }
    [void]$script:issuesSeen.Add($key)
    [System.IO.File]::AppendAllText($issuesPath, "[$Source] $Line`n", $utf8)
}

function Write-FullVerifyIssuesFromLog {
    param(
        [string]$Source,
        [string]$LogPath
    )
    if (-not (Test-Path -LiteralPath $LogPath)) { return }
    foreach ($line in [System.IO.File]::ReadLines($LogPath)) {
        Add-FullVerifyIssue -Source $Source -Line $line
    }
}

function Finalize-FullVerifyIssuesFile {
    param([int]$FailCount)
    [System.IO.File]::AppendAllText($issuesPath, "`n=== Post-scan step logs (deze run) ===`n", $utf8)
    foreach ($logPath in $script:stepLogFiles) {
        if (-not (Test-Path -LiteralPath $logPath)) { continue }
        $src = Split-Path -Leaf $logPath
        Write-FullVerifyIssuesFromLog -Source $src -LogPath $logPath
    }
    $summary = @(
        ""
        "=== Summary ==="
        "Failed steps: $FailCount"
        "Unique issue lines: $($script:issuesSeen.Count)"
        "Detail logs: $logDir\FULL_VERIFY_*.log"
        ""
    ) -join "`n"
    [System.IO.File]::AppendAllText($issuesPath, $summary, $utf8)
    if ($script:issuesSeen.Count -eq 0) {
        [System.IO.File]::AppendAllText($issuesPath, "(geen fails/warnings/errors gevangen)`n", $utf8)
    }
}

Initialize-FullVerifyIssuesFile
Write-Host "[INFO] Issues-rapport: $issuesPath" -ForegroundColor DarkGray

# Live batch/API integration tests are opt-in; do not inherit a developer shell flag.
if ($env:HERMES_RUN_LIVE_BATCH) {
    Remove-Item Env:\HERMES_RUN_LIVE_BATCH -ErrorAction SilentlyContinue
    Write-Host '[INFO] HERMES_RUN_LIVE_BATCH unset for FULL_VERIFICATION (opt-in only).' -ForegroundColor DarkGray
}

function Invoke-VerifyStep {
    param(
        [string]$Name,
        [string]$LogFile,
        [scriptblock]$Action
    )
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    $logPath = Join-Path $logDir $LogFile
    if (-not $script:stepLogFiles.Contains($logPath)) {
        $script:stepLogFiles.Add($logPath) | Out-Null
    }
    if (Test-Path -LiteralPath $logPath) { Remove-Item -LiteralPath $logPath -Force }
    # Touch log early so long steps (parallel pytest) leave a trace even if killed mid-run.
    [System.IO.File]::WriteAllText($logPath, "STEP:$Name`nSTART:$(Get-Date -Format o)`n", $utf8)
    $code = 0
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Action 2>&1 | ForEach-Object {
            $line = if ($_ -is [System.Management.Automation.ErrorRecord]) {
                $_.ToString()
            } else {
                "$_"
            }
            Write-Host $line
            [System.IO.File]::AppendAllText($logPath, $line + "`n", $utf8)
            Add-FullVerifyIssue -Source $Name -Line $line
        }
        $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
    } catch {
        $errLine = $_.Exception.Message
        [System.IO.File]::AppendAllText($logPath, $errLine + "`n", $utf8)
        Add-FullVerifyIssue -Source $Name -Line "ERROR $errLine"
        $code = 1
    } finally {
        $ErrorActionPreference = $prevEap
    }
    [System.IO.File]::AppendAllText($logPath, "END:$(Get-Date -Format o)`nEXIT:$code`n", $utf8)
    if ($code -eq 0) {
        Write-Host "[OK] $Name" -ForegroundColor Green
    } else {
        $failLine = "[FAIL] $Name (exit $code) - zie $logPath"
        Write-Host $failLine -ForegroundColor Red
        Add-FullVerifyIssue -Source $Name -Line $failLine
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

Finalize-FullVerifyIssuesFile -FailCount $failures

Write-Host ""
Write-Host "[INFO] Issues-rapport: $issuesPath" -ForegroundColor Cyan
if ($failures -gt 0) {
    Write-Host "FULL_VERIFICATION: $failures stap(pen) gefaald." -ForegroundColor Red
    exit 1
}
Write-Host "FULL_VERIFICATION: alles geslaagd." -ForegroundColor Green
exit 0
