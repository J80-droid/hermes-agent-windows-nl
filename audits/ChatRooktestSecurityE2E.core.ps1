# Chat rooktest + security pins E2E — overlay path, config rebind, auth BOM (no live API).
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
    $fallback = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if (Test-Path -LiteralPath $fallback) { return $fallback }
    return 'python'
}

$harness = Join-Path $scriptRoot 'ChatRooktestSecurityE2E.harness.py'
if (-not (Test-Path -LiteralPath $harness)) {
    Write-Host '[FAIL] ChatRooktestSecurityE2E.harness.py ontbreekt' -ForegroundColor Red
    exit 1
}

$python = Get-HermesAuditPython
Write-Host "=== ChatRooktestSecurityE2E (python: $python) ===" -ForegroundColor Cyan
Push-Location $RepoRoot
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $python $harness
$code = $LASTEXITCODE
$ErrorActionPreference = $prevEap
Pop-Location
if ($code -ne 0) { exit $code }
Write-Host 'RUN_CHAT_ROOKTEST_SECURITY_E2E: ALL PASS' -ForegroundColor Green
exit 0
