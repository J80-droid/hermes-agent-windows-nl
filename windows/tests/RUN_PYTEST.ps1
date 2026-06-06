# Hermes Agent — pytest shim (backward compat).
# Default: fork gate (manifest SSOT). Volledige upstream suite: -Upstream of -ReportOnly.
# Zie windows/tests/PYTEST_POLICY.md
param(
    [switch]$Upstream,
    [switch]$ReportOnly
)

$ErrorActionPreference = 'Stop'

$testsDir = $PSScriptRoot
$windowsDir = Split-Path -Parent $testsDir

if ($Upstream -or $ReportOnly) {
    $upstreamScript = Join-Path $testsDir 'RUN_PYTEST_UPSTREAM.ps1'
    $upstreamArgs = @()
    if ($ReportOnly) { $upstreamArgs += '-ReportOnly' }
    if ($args) { $upstreamArgs += $args }
    & $upstreamScript @upstreamArgs
    exit $LASTEXITCODE
}

Write-Host 'RUN_PYTEST.ps1: default is fork gate (manifest). Volledige upstream: -Upstream of RUN_PYTEST_UPSTREAM.bat -ReportOnly' -ForegroundColor DarkYellow
$gateScript = Join-Path $testsDir 'RUN_PYTEST_FORK_GATE.ps1'
& $gateScript @args
exit $LASTEXITCODE
