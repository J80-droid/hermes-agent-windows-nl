#requires -Version 5.1
# Unit tests: LegalDomainE2E.core.ps1 met geïsoleerde paden (geen Pester-module — Hermes assert-runner).
# Draai: powershell -NoProfile -ExecutionPolicy Bypass -File windows/tests/LegalDomainE2E.Unit.Tests.ps1
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$corePath = Join-Path $repoRoot 'windows/audits/LegalDomainE2E.core.ps1'
$launcherPath = Join-Path $repoRoot 'windows/audits/RUN_LEGAL_DOMAIN_E2E.ps1'
$templateSoul = Join-Path $repoRoot 'docs/templates/SOUL_LEGAL_DOMAIN.md'

$script:UnitFailed = 0
$isoRoot = Join-Path $env:TEMP ('hermes_legal_e2e_unit_' + [Guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $isoRoot -Force | Out-Null

$prevLocal = $env:LOCALAPPDATA
$prevUser = $env:USERPROFILE
$prevStrict = $env:HERMES_LEGAL_VERIFY_STRICT
$prevDomains = $env:HERMES_DOMAINS_YAML
$prevAuditPy = $env:HERMES_AUDIT_PYTHON
$prevSkipPytest = $env:HERMES_LEGAL_E2E_SKIP_PYTEST
$prevSkipRook = $env:HERMES_LEGAL_E2E_SKIP_ROOKTEST
$prevSkipReady = $env:HERMES_LEGAL_E2E_SKIP_READINESS
$prevSkipPython = $env:HERMES_LEGAL_E2E_SKIP_PYTHON_STEPS

$env:HERMES_LEGAL_E2E_SKIP_PYTEST = '1'
$env:HERMES_LEGAL_E2E_SKIP_ROOKTEST = '1'
$env:HERMES_LEGAL_E2E_SKIP_READINESS = '1'
$env:HERMES_LEGAL_E2E_SKIP_PYTHON_STEPS = '1'

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        Write-Host ('FAIL: ' + $Message) -ForegroundColor Red
        $script:UnitFailed++
    }
}

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) {
        Write-Host ('FAIL: ' + $Message + " (expected='$Expected' actual='$Actual')") -ForegroundColor Red
        $script:UnitFailed++
    }
}

function Get-UnitAuditPython {
    if ($env:HERMES_AUDIT_PYTHON -and (Test-Path -LiteralPath $env:HERMES_AUDIT_PYTHON)) {
        return $env:HERMES_AUDIT_PYTHON.Trim()
    }
    foreach ($candidate in @(
            (Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'),
            (Join-Path $env:USERPROFILE 'anaconda3\envs\hermes-env\python.exe')
        )) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
    return $null
}

function Initialize-LegalE2EUnitLayout {
    param(
        [string]$Root,
        [string]$Repo,
        [switch]$IncludeSourceTree
    )
    $userHome = Join-Path $Root 'userhome'
    $localApp = Join-Path $Root 'localappdata'
    $dataRoot = Join-Path $userHome 'data'
    $hermesRoot = Join-Path $localApp 'hermes'
    $legalProf = Join-Path $hermesRoot 'profiles\legal'
    $coreProf = Join-Path $hermesRoot 'profiles\core'

    New-Item -ItemType Directory -Path (Join-Path $legalProf 'memories') -Force | Out-Null
    New-Item -ItemType Directory -Path $coreProf -Force | Out-Null
    New-Item -ItemType File -Path (Join-Path $hermesRoot 'config.yaml') -Force | Out-Null

    Copy-Item -LiteralPath $templateSoul -Destination (Join-Path $legalProf 'SOUL.md') -Force
    Copy-Item -LiteralPath $templateSoul -Destination (Join-Path $coreProf 'SOUL.md') -Force

    $userMd = @'
# USER.md (unit fixture)
no pleaser-behavior; direct forensic tone for legal profile.
'@
    Set-Content -LiteralPath (Join-Path $legalProf 'memories\USER.md') -Value $userMd -Encoding UTF8

    $matters = @'
# Actieve zaken (unit)
## Zaak: GCR 2024-00145
| Veld | Inhoud |
|------|--------|
| Instantie | GCR 2024-00145 |
'@
    Set-Content -LiteralPath (Join-Path $legalProf 'LEGAL_ACTIVE_MATTERS.md') -Value $matters -Encoding UTF8

    $domainsDir = $dataRoot
    New-Item -ItemType Directory -Path $domainsDir -Force | Out-Null
    $domainsYaml = Join-Path $domainsDir 'domains.yaml'
    @'
domains:
  - name: legal
    mcp: lancedb-legal
'@ | Set-Content -LiteralPath $domainsYaml -Encoding UTF8

    if ($IncludeSourceTree) {
        $rawLegal = Join-Path $dataRoot 'raw_source_files\04_Legal_Corporate'
        foreach ($d in @(
                'Arbeidsrecht', 'Bestuursrecht', 'Aansprakelijkheid_Letselschade',
                'Klokkenluiders', 'Corporate', '_Taxonomy'
            )) {
            New-Item -ItemType Directory -Path (Join-Path $rawLegal $d) -Force | Out-Null
        }
    }

    return @{
        UserHome     = $userHome
        LocalAppData = $localApp
        HermesRoot   = $hermesRoot
        UserDataRoot = $dataRoot
        DomainsYaml  = $domainsYaml
    }
}

function Invoke-LegalE2ECoreProcess {
    param(
        [hashtable]$Layout,
        [switch]$StrictSources
    )
    $env:LOCALAPPDATA = $Layout.LocalAppData
    $env:USERPROFILE = $Layout.UserHome
    $env:HERMES_DOMAINS_YAML = $Layout.DomainsYaml
    $env:HERMES_REPO_ROOT = $repoRoot
    if ($StrictSources) {
        $env:HERMES_LEGAL_VERIFY_STRICT = '1'
    } else {
        Remove-Item -Path Env:HERMES_LEGAL_VERIFY_STRICT -ErrorAction SilentlyContinue
    }

    $invokeArgs = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $corePath,
        '-RepoRoot', $repoRoot,
        '-HermesRoot', $Layout.HermesRoot,
        '-UserDataRoot', $Layout.UserDataRoot
    )
    if ($StrictSources) { $invokeArgs += '-StrictSources' }
    & powershell @invokeArgs | Out-Null
    return [int]$LASTEXITCODE
}

try {
    $auditPy = Get-UnitAuditPython
    if ($auditPy) { $env:HERMES_AUDIT_PYTHON = $auditPy }

    # --- Syntax: core + launcher ---
    $parseErr = [System.Collections.Generic.List[object]]::new()
    $null = [System.Management.Automation.Language.Parser]::ParseFile($corePath, [ref]$null, [ref]$parseErr)
    Assert-True ($parseErr.Count -eq 0) 'LegalDomainE2E.core.ps1 parse'
    $parseErr.Clear()
    $null = [System.Management.Automation.Language.Parser]::ParseFile($launcherPath, [ref]$null, [ref]$parseErr)
    Assert-True ($parseErr.Count -eq 0) 'RUN_LEGAL_DOMAIN_E2E.ps1 parse'

    # --- StrictSources + volledige fixture -> PASS (zonder python/readiness/rook) ---
    $layoutOk = Initialize-LegalE2EUnitLayout -Root $isoRoot -Repo $repoRoot -IncludeSourceTree
    $codeOk = Invoke-LegalE2ECoreProcess -Layout $layoutOk -StrictSources
    Assert-Equal 0 $codeOk 'StrictSources met bron-submappen moet PASS'

    # --- StrictSources zonder bronmap -> FAIL ---
    $isoFail = Join-Path $env:TEMP ('hermes_legal_e2e_fail_' + [Guid]::NewGuid().ToString('n'))
    New-Item -ItemType Directory -Path $isoFail -Force | Out-Null
    $layoutFail = Initialize-LegalE2EUnitLayout -Root $isoFail -Repo $repoRoot
    $codeFail = Invoke-LegalE2ECoreProcess -Layout $layoutFail -StrictSources
    Assert-True ($codeFail -ne 0) 'StrictSources zonder bronmap moet FAIL'

    # --- Niet-strict zonder bronmap -> PASS (SKIP stap 6) ---
    $isoSkip = Join-Path $env:TEMP ('hermes_legal_e2e_skip_' + [Guid]::NewGuid().ToString('n'))
    New-Item -ItemType Directory -Path $isoSkip -Force | Out-Null
    $layoutSkip = Initialize-LegalE2EUnitLayout -Root $isoSkip -Repo $repoRoot
    Remove-Item -Path Env:HERMES_LEGAL_VERIFY_STRICT -ErrorAction SilentlyContinue
    $codeSkip = Invoke-LegalE2ECoreProcess -Layout $layoutSkip
    Assert-Equal 0 $codeSkip 'Zonder StrictSources en zonder bronmap: SKIP, geen FAIL'

    # --- GCR in Identity detectie ---
    $badSoul = Join-Path $layoutOk.HermesRoot 'profiles\legal\SOUL.md'
    $soulText = Get-Content -LiteralPath $badSoul -Raw -Encoding UTF8
    $cut = $soulText.IndexOf('## Values')
    if ($cut -lt 0) { $cut = $soulText.IndexOf('## Expertise') }
    if ($cut -lt 0) { $cut = [Math]::Min(400, $soulText.Length) }
    $soulBad = $soulText.Substring(0, $cut) + "`nGCR 2024-00145`n" + $soulText.Substring($cut)
    Set-Content -LiteralPath $badSoul -Value $soulBad -Encoding UTF8
    $codeGcr = Invoke-LegalE2ECoreProcess -Layout $layoutOk -StrictSources
    Assert-True ($codeGcr -ne 0) 'GCR in Identity-blok moet FAIL'

    Write-Host ''
    if ($script:UnitFailed -eq 0) {
        Write-Host 'LegalDomainE2E.Unit.Tests: ALL PASS' -ForegroundColor Green
        exit 0
    }
    Write-Host ("LegalDomainE2E.Unit.Tests: $script:UnitFailed failure(s)") -ForegroundColor Red
    exit 1
}
finally {
    $env:LOCALAPPDATA = $prevLocal
    $env:USERPROFILE = $prevUser
    if ($null -ne $prevStrict) { $env:HERMES_LEGAL_VERIFY_STRICT = $prevStrict }
    else { Remove-Item -Path Env:HERMES_LEGAL_VERIFY_STRICT -ErrorAction SilentlyContinue }
    if ($null -ne $prevDomains) { $env:HERMES_DOMAINS_YAML = $prevDomains }
    else { Remove-Item -Path Env:HERMES_DOMAINS_YAML -ErrorAction SilentlyContinue }
    if ($null -ne $prevAuditPy) { $env:HERMES_AUDIT_PYTHON = $prevAuditPy }
    else { Remove-Item -Path Env:HERMES_AUDIT_PYTHON -ErrorAction SilentlyContinue }
    if ($null -ne $prevSkipPytest) { $env:HERMES_LEGAL_E2E_SKIP_PYTEST = $prevSkipPytest }
    else { Remove-Item -Path Env:HERMES_LEGAL_E2E_SKIP_PYTEST -ErrorAction SilentlyContinue }
    if ($null -ne $prevSkipRook) { $env:HERMES_LEGAL_E2E_SKIP_ROOKTEST = $prevSkipRook }
    else { Remove-Item -Path Env:HERMES_LEGAL_E2E_SKIP_ROOKTEST -ErrorAction SilentlyContinue }
    if ($null -ne $prevSkipReady) { $env:HERMES_LEGAL_E2E_SKIP_READINESS = $prevSkipReady }
    else { Remove-Item -Path Env:HERMES_LEGAL_E2E_SKIP_READINESS -ErrorAction SilentlyContinue }
    if ($null -ne $prevSkipPython) { $env:HERMES_LEGAL_E2E_SKIP_PYTHON_STEPS = $prevSkipPython }
    else { Remove-Item -Path Env:HERMES_LEGAL_E2E_SKIP_PYTHON_STEPS -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath $isoRoot) { Remove-Item -LiteralPath $isoRoot -Recurse -Force -ErrorAction SilentlyContinue }
}
