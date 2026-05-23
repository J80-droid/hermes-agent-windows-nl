# Trust en Forensic protocol E2E — implementatie (dot-source alleen hier; niet in RUN_*.ps1).
param(
    [string]$RepoRoot = ''
)

$windowsRoot = Join-Path $PSScriptRoot '..'
. (Join-Path $windowsRoot 'HermesShellCommon.ps1')
. (Join-Path $windowsRoot 'scripts\MemoryAuditCommon.ps1')
. (Join-Path $windowsRoot 'HermesTrustForensicPatterns.ps1')
. (Join-Path $windowsRoot 'HermesTrustForensicProfileChecks.ps1')

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

function Get-HermesRoot {
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

$failures = 0
$hermesRoot = Get-HermesRoot

Write-Host '=== Trust en Forensic E2E ===' -ForegroundColor Cyan

$repoFiles = @(
    'docs/templates/SOUL_SHARED_ADVISORY.md',
    'docs/templates/SOUL_SHARED_VALUES.md',
    'docs/templates/SOUL_SHARED_TRUST_VERIFICATION.md',
    'docs/templates/MEMORY_CANONICAL_SEED.md',
    'docs/templates/SOUL_LEGAL_DOMAIN.md'
)
$docTrustForensic = 'docs/TRUST_' + 'FORENSIC_PROTOCOL.md'
foreach ($rel in ($repoFiles + $docTrustForensic)) {
    $p = Join-Path $RepoRoot ($rel -replace '/', '\')
    if (-not (Test-Path -LiteralPath $p)) {
        Write-Host ('[FAIL] ' + 'Ontbreekt: ' + $rel) -ForegroundColor Red
        $failures++
    }
}
$legalTpl = Get-Content -LiteralPath (Join-Path $RepoRoot 'docs/templates/SOUL_LEGAL_DOMAIN.md') -Raw -Encoding UTF8
if (-not (Test-HermesSoulLegalForensicTrust -Text $legalTpl)) {
    Write-Host '[FAIL] SOUL_LEGAL_DOMAIN mist Forensic en trust' -ForegroundColor Red
    $failures++
}

$legalMem = Join-Path $hermesRoot 'profiles/legal/memories'
if (-not (Test-Path -LiteralPath $legalMem)) {
    Write-Host '[FAIL] profiles/legal/memories ontbreekt' -ForegroundColor Red
    $failures++
}

$failures += Invoke-HermesTrustForensicProfileChecks -HermesRoot $hermesRoot

$legalSoul = Join-Path $hermesRoot 'profiles/legal/SOUL.md'
if (Test-Path -LiteralPath $legalSoul) {
    $ls = Get-Content -LiteralPath $legalSoul -Raw -Encoding UTF8
    if (-not (Test-HermesSoulLegalForensicTrust -Text $ls)) {
        Write-Host '[FAIL] legal SOUL mist Forensic en trust' -ForegroundColor Red
        $failures++
    }
}

$configFails = Test-AllProfileMemoryConfigLimits -HermesRoot $hermesRoot
foreach ($cf in $configFails) {
    Write-Host ('[FAIL] config: ' + $cf) -ForegroundColor Red
    $failures++
}

$conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
$pytestTrustDocs = Join-Path $RepoRoot 'tests/windows/test_trust_forensic_docs.py'
$pytestScrub = Join-Path $RepoRoot 'tests/windows/test_scrub_identity.py'
$pytestFiles = @($pytestTrustDocs, $pytestScrub)
foreach ($pytestFile in $pytestFiles) {
    if (-not (Test-Path -LiteralPath $pytestFile)) {
        continue
    }
    if (Test-Path -LiteralPath $conda) {
        & $conda run -n hermes-env --no-capture-output python -m pytest $pytestFile -q --tb=short | ForEach-Object { Write-Host $_ }
    } elseif ($env:HERMES_AUDIT_PYTHON) {
        & $env:HERMES_AUDIT_PYTHON -m pytest $pytestFile -q --tb=short | ForEach-Object { Write-Host $_ }
    } else {
        & python -m pytest $pytestFile -q --tb=short | ForEach-Object { Write-Host $_ }
    }
    if (Test-NativeCommandFailed) { $failures++ }
}

if ($failures -gt 0) {
    Write-Host ('=== TRUST FORENSIC E2E: FAIL ({0}) ===' -f $failures) -ForegroundColor Red
    exit 1
}
Write-Host '=== TRUST FORENSIC E2E: PASS ===' -ForegroundColor Green
exit 0
