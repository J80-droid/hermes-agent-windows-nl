# Upstream sync fase-2 E2E — dunne launcher.
param(
    [string]$RepoRoot = '',
    [switch]$SkipVitest
)

$ErrorActionPreference = 'Stop'
$coreScript = Join-Path $PSScriptRoot 'UpstreamSyncPhase2E2E.core.ps1'
if (-not (Test-Path -LiteralPath $coreScript)) {
    Write-Host '[FAIL] UpstreamSyncPhase2E2E.core.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}
& $coreScript @PSBoundParameters
exit $LASTEXITCODE
