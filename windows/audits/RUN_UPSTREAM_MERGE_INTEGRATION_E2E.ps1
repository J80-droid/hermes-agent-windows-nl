# Upstream merge integration E2E — dunne launcher.
param(
    [string]$RepoRoot = '',
    [switch]$SkipVitest,
    [switch]$SkipPytest
)

$ErrorActionPreference = 'Stop'
$coreScript = Join-Path $PSScriptRoot 'UpstreamMergeIntegrationE2E.core.ps1'
if (-not (Test-Path -LiteralPath $coreScript)) {
    Write-Host '[FAIL] UpstreamMergeIntegrationE2E.core.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}
& $coreScript @PSBoundParameters
exit $LASTEXITCODE
