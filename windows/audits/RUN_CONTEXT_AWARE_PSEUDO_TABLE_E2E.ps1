# Context-aware pseudo-tabel normalizer E2E — dunne launcher.
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest,
    [switch]$SkipTsParity
)

$ErrorActionPreference = 'Stop'
$coreScript = Join-Path $PSScriptRoot 'ContextAwarePseudoTableE2E.core.ps1'
if (-not (Test-Path -LiteralPath $coreScript)) {
    Write-Host '[FAIL] ContextAwarePseudoTableE2E.core.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}
& $coreScript @PSBoundParameters
exit $LASTEXITCODE
