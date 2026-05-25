# Root config inheritance E2E — dunne launcher.
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest,
    [switch]$SkipLive
)

$ErrorActionPreference = 'Stop'
$coreScript = Join-Path $PSScriptRoot 'RootConfigInheritanceE2E.core.ps1'
if (-not (Test-Path -LiteralPath $coreScript)) {
    Write-Host '[FAIL] RootConfigInheritanceE2E.core.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}
& $coreScript @PSBoundParameters
exit $LASTEXITCODE
