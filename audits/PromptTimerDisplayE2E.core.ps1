# Prompt timer display (no emoji) E2E launcher.
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
    $fallback = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if (Test-Path -LiteralPath $fallback) { return $fallback }
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

$harness = Join-Path $scriptRoot 'PromptTimerDisplayE2E.harness.py'
if (-not (Test-Path -LiteralPath $harness)) {
    Write-Host '[FAIL] PromptTimerDisplayE2E.harness.py ontbreekt' -ForegroundColor Red
    exit 1
}

$python = Get-HermesAuditPython
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$reportPath = Join-Path $scriptRoot ("PROMPT_TIMER_DISPLAY_E2E_REPORT_" + $reportStamp + '.md')

Write-Host "=== Prompt Timer Display E2E (python: $python) ===" -ForegroundColor Cyan
Push-Location $RepoRoot
$logPath = Join-Path $scriptRoot ("PROMPT_TIMER_DISPLAY_E2E_LOG_" + $reportStamp + '.txt')
try {
    & $python $harness 2>&1 | Tee-Object -FilePath $logPath
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

$status = if ($exitCode -eq 0) { 'PASS' } else { 'FAIL' }
$logText = ''
if (Test-Path -LiteralPath $logPath) {
    $logText = Get-Content -LiteralPath $logPath -Raw -Encoding UTF8
}
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Prompt Timer Display E2E - $status")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$sb.AppendLine("Repo: ``$RepoRoot``")
[void]$sb.AppendLine("Python: ``$python``")
[void]$sb.AppendLine('')
if ($logText) {
    [void]$sb.AppendLine('## Log')
    [void]$sb.AppendLine('```')
    [void]$sb.AppendLine($logText.TrimEnd())
    [void]$sb.AppendLine('```')
}
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($exitCode -ne 0) {
    Write-Host '=== PROMPT TIMER DISPLAY E2E: FAIL ===' -ForegroundColor Red
    exit 1
}
Write-Host '=== PROMPT TIMER DISPLAY E2E: PASS ===' -ForegroundColor Green
exit 0
