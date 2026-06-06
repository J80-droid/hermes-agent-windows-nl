#requires -Version 5.1
<#
.SYNOPSIS
  Snelle legal runtime verify (wrapper; volledige poort: RUN_LEGAL_DOMAIN_E2E.bat).

.CHECKS
  ensure_legal_active_matters, runtime legal/core SOUL meta, domains.yaml (legal + lancedb-legal),
  verify_legal_lens_parity.py --all (conda hermes-env).

.EXIT
  0 = OK (of warn-only zonder HERMES_LEGAL_VERIFY_STRICT=1)
  1 = FAIL (strict) of parity/SOUL/meta/domains
#>
param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$script:LegalVerifyQuiet = [bool]$Quiet

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

$strict = ($env:HERMES_LEGAL_VERIFY_STRICT -eq '1')
$failures = 0

if (-not $RepoRoot) {
    if ($env:HERMES_REPO_ROOT) { $RepoRoot = $env:HERMES_REPO_ROOT.Trim().Trim('"') }
    else { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

function Write-Verify {
    param([string]$Message, [string]$Level = 'Info')
    if ($script:LegalVerifyQuiet -and $Level -eq 'Detail') { return }
    switch ($Level) {
        'Ok' { Write-HermesOk $Message }
        'Warn' { Write-HermesWarn $Message }
        'Fail' { Write-Host "[FAIL] $Message" -ForegroundColor Red }
        default { Write-Host $Message }
    }
}

& (Join-Path $PSScriptRoot 'ensure_legal_active_matters.ps1') -RepoRoot $RepoRoot -Quiet
if (Test-NativeCommandFailed) { $failures++ }

$hermesRoot = Join-Path $env:LOCALAPPDATA 'hermes'
if (-not (Test-Path -LiteralPath (Join-Path $hermesRoot 'config.yaml'))) {
    $hermesRoot = Join-Path $env:USERPROFILE '.hermes'
}

$domainsYaml = if ($env:HERMES_DOMAINS_YAML) { $env:HERMES_DOMAINS_YAML } else { Join-Path $env:USERPROFILE 'data\domains.yaml' }
if (-not (Test-Path -LiteralPath $domainsYaml)) {
    Write-Verify "domains.yaml ontbreekt: $domainsYaml (zie docs/domains.yaml.example)" -Level Warn
    if ($strict) { $failures++ }
} else {
    try {
        $dy = Get-Content -LiteralPath $domainsYaml -Raw -Encoding UTF8
    } catch {
        Write-Verify "domains.yaml niet leesbaar: $domainsYaml" -Level Fail
        $failures++
        $dy = ''
    }
    if ($dy -and $dy -notmatch '(?m)^\s*-\s*name:\s*legal\b' -and $dy -notmatch '(?m)^legal:') {
        Write-Verify 'domains.yaml: geen legal entry' -Level Warn
        if ($strict) { $failures++ }
    } elseif ($dy -and $dy -notmatch 'lancedb-legal') {
        Write-Verify 'domains.yaml: legal zonder lancedb-legal MCP-verwijzing' -Level Warn
        if ($strict) { $failures++ }
    } elseif ($dy) {
        Write-Verify 'domains.yaml: legal entry aanwezig' -Level Ok
    }
}

$legalSoul = Join-Path $hermesRoot 'profiles\legal\SOUL.md'
if (-not (Test-Path -LiteralPath $legalSoul)) {
    Write-Verify "Runtime legal SOUL ontbreekt: $legalSoul" -Level Fail
    $failures++
} else {
    $soul = Get-Content -LiteralPath $legalSoul -Raw -Encoding UTF8
    if ($soul -notmatch '## Juridische lenzen') {
        Write-Verify 'Runtime SOUL: ## Juridische lenzen ontbreekt' -Level Fail
        $failures++
    }
    if ($soul -notmatch 'Domeinarchitectuur|/legal-architectuur') {
        Write-Verify 'Runtime SOUL: meta Domeinarchitectuur ontbreekt (deploy SOUL)' -Level Fail
        $failures++
    }
    if ($soul -notmatch 'LEGAL_ACTIVE_MATTERS') {
        Write-Verify 'Runtime SOUL vermeldt LEGAL_ACTIVE_MATTERS niet' -Level Warn
        if ($strict) { $failures++ }
    }
}

$coreSoul = Join-Path $hermesRoot 'profiles\core\SOUL.md'
if (Test-Path -LiteralPath $coreSoul) {
    $core = Get-Content -LiteralPath $coreSoul -Raw -Encoding UTF8
    if ($core -notmatch 'Legal architectuur|/legal-architectuur') {
        Write-Verify 'Runtime core SOUL: Legal architectuur meta ontbreekt' -Level Warn
        if ($strict) { $failures++ }
    }
}

$conda = $null
foreach ($p in @(
    (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
    (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe')
)) {
    if ($p -and (Test-Path -LiteralPath $p)) { $conda = $p; break }
}
if ($conda) {
    $python = (& $conda run -n hermes-env python -c "import sys; print(sys.executable)" 2>&1 | Select-Object -Last 1).Trim()
    $parity = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/verify_legal_lens_parity.py'
    & $python $parity --all
    if (Test-NativeCommandFailed) {
        Write-Verify 'Lenzentabel parity mislukt (sync: SYNC_LEGAL_LENS_FROM_TAXONOMY.bat)' -Level Fail
        $failures++
    }
} else {
    Write-Verify 'conda niet gevonden — parity overgeslagen' -Level Warn
}

if ($failures -gt 0) {
    if ($strict) { exit 1 }
    Write-Verify "VERIFY_LEGAL_RUNTIME: $failures waarschuwing(en) (niet strict)" -Level Warn
    exit 0
}
Write-Verify 'VERIFY_LEGAL_RUNTIME: PASS' -Level Ok
exit 0
