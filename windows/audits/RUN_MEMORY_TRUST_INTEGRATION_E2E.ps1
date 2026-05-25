# Launcher: geïntegreerde memory-trust E2E (alleen deze audit draaien).
param([string]$RepoRoot = '')

$ErrorActionPreference = 'Stop'
$coreScript = Join-Path $PSScriptRoot 'MemoryTrustIntegrationE2E.core.ps1'
if (-not (Test-Path -LiteralPath $coreScript)) {
    Write-Host 'FAIL: MemoryTrustIntegrationE2E.core.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}
& $coreScript @PSBoundParameters
exit $LASTEXITCODE
