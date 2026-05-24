# Pseudo-tabel normalizer E2E — dunne launcher (geen dot-source: stabiel in IDE/PSES).
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest,
    [switch]$SkipTsParity
)

$ErrorActionPreference = 'Stop'
$coreScript = Join-Path $PSScriptRoot 'PseudoTableNormalizerE2E.core.ps1'
if (-not (Test-Path -LiteralPath $coreScript)) {
    Write-Host '[FAIL] PseudoTableNormalizerE2E.core.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}
& $coreScript @PSBoundParameters
exit $LASTEXITCODE
