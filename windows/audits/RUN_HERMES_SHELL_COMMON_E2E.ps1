# HermesShellCommon PSES E2E — dunne launcher.
param([string]$RepoRoot = '')

$ErrorActionPreference = 'Stop'
$coreScript = Join-Path $PSScriptRoot 'HermesShellCommonE2E.core.ps1'
if (-not (Test-Path -LiteralPath $coreScript)) {
    Write-Host 'FAIL: HermesShellCommonE2E.core.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}
& $coreScript @PSBoundParameters
exit $LASTEXITCODE
