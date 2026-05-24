# Hermes split-home E2E — dunne launcher.
param(
    [string]$RepoRoot = '',
    [switch]$StrictDrift
)

$ErrorActionPreference = 'Stop'
$coreScript = Join-Path $PSScriptRoot 'HermesHomeE2E.core.ps1'
if (-not (Test-Path -LiteralPath $coreScript)) {
    Write-Host '[FAIL] HermesHomeE2E.core.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}
& $coreScript @PSBoundParameters
exit $LASTEXITCODE
