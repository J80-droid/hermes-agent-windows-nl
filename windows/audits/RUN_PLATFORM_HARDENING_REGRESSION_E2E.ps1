# Platform hardening regression E2E — dunne launcher.
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest
)

$ErrorActionPreference = 'Stop'
$coreScript = Join-Path $PSScriptRoot 'PlatformHardeningRegressionE2E.core.ps1'
if (-not (Test-Path -LiteralPath $coreScript)) {
    Write-Host '[FAIL] PlatformHardeningRegressionE2E.core.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}
& $coreScript @PSBoundParameters
exit $LASTEXITCODE
