# Dunne launcher: legal domein E2E (implementatie in LegalDomainE2E.core.ps1).
param(
    [switch]$StrictSources,
    [switch]$ApplyLensSync
)

$ErrorActionPreference = 'Stop'
$coreScript = Join-Path $PSScriptRoot 'LegalDomainE2E.core.ps1'
if (-not (Test-Path -LiteralPath $coreScript)) {
    Write-Host '[FAIL] LegalDomainE2E.core.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}
& $coreScript @PSBoundParameters
exit $LASTEXITCODE
