# E2E: SOUL anatomy — repo templates + runtime SOUL.md

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

Set-Location $repoRoot



Write-Host '=== SOUL Anatomy E2E ===' -ForegroundColor Cyan



$requiredTemplates = @(

    'docs/templates/SOUL_ANATOMY_BASE.md',

    'docs/templates/SOUL_SHARED_VALUES.md',

    'docs/templates/SOUL_SHARED_INTERACTION.md',

    'docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md',

    'docs/templates/SOUL_SHARED_CODEBASE_AUDIT.md',

    'docs/templates/CODEBASE_AUDIT_REPORT.md',

    'docs/CODEBASE_AUDIT_EVIDENCE.md',

    'docs/templates/SOUL_SHARED_WORKFLOW.md',

    'docs/templates/SOUL_SHARED_MEMORY_POLICY.md',

    'docs/templates/SOUL_SHARED_TRUST_VERIFICATION.md',

    'docs/templates/SOUL_SHARED_TOOL_GOVERNANCE.md',

    'docs/templates/SOUL_CORE_ORCHESTRATOR.md',

    'docs/templates/SOUL_LEGAL_DOMAIN.md',

    'docs/templates/SOUL_ACADEMICS_DOMAIN.md',

    'docs/templates/SOUL_OPERATIONS_DOMAIN.md',

    'docs/templates/SOUL_TRADING_DOMAIN.md',

    'docs/templates/SOUL_GAMING_DOMAIN.md',

    'docs/templates/SOUL_PHILOSOPHY_DOMAIN.md',

    'docs/templates/SOUL_LOGISTICS_DOMAIN.md',

    'docs/templates/SOUL_VENTURES_DOMAIN.md',

    'docs/templates/SOUL_DATA_DOMAIN.md',

    'docs/templates/SOUL_DEV_DOMAIN.md',

    'docs/templates/SOUL_SECURITY_DOMAIN.md',

    'docs/templates/SOUL_ICT_DOMAIN.md',

    'docs/SOUL_ANATOMY_SPEC.md'

)



$missing = @()

foreach ($rel in $requiredTemplates) {

    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $rel))) {

        $missing += $rel

    }

}

if ($missing.Count -gt 0) {

    foreach ($m in $missing) { Write-Host ('[FAIL] ' + 'Ontbreekt: ' + $m) -ForegroundColor Red }

    exit 1

}

Write-Host '[OK] Alle repo anatomy-templates aanwezig' -ForegroundColor Green



function Test-RepoSoulTemplatesAnatomy {

    param([string]$Root)

    $templateFail = $false

    $paths = @(Get-ChildItem (Join-Path $Root 'docs/templates') -Filter 'SOUL_*_DOMAIN.md')

    $paths += Get-Item (Join-Path $Root 'docs/templates/SOUL_CORE_ORCHESTRATOR.md')

    foreach ($f in $paths) {

        $t = Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8

        if ($t -notmatch '# SOUL\.md - ') {

            $templateFail = $true

            Write-Host ('[FAIL] ' + $($f.Name) + ': mist anatomy header') -ForegroundColor Red

        }

        if ($t -notmatch '## Example Interaction') {

            $templateFail = $true

            Write-Host ('[FAIL] ' + $($f.Name) + ': mist Example Interaction') -ForegroundColor Red

        }

        if ($t -notmatch '## Expertise & Knowledge') {

            $templateFail = $true

            Write-Host ('[FAIL] ' + $($f.Name) + ': mist Expertise & Knowledge') -ForegroundColor Red

        }

        if ($t -notmatch '### Output conventions \(institutional\)') {

            $templateFail = $true

            Write-Host ('[FAIL] ' + $($f.Name) + ': mist Output conventions stub') -ForegroundColor Red

        }

    }

    return -not $templateFail

}



$validateScript = Join-Path $repoRoot 'scripts/validate_soul_anatomy.py'

$pyOk = $false

if (Test-Path -LiteralPath $validateScript) {

    try {

        $null = & py -3 $validateScript --repo-templates 2>&1

        if ($LASTEXITCODE -eq 0) { $pyOk = $true }

    } catch {
        Write-Verbose 'py -3 ontbreekt of faalde; PowerShell fallback hieronder.'
    }

}

if ($pyOk) {

    Write-Host '[OK] Repo templates anatomy-validatie (python)' -ForegroundColor Green

} elseif (-not (Test-RepoSoulTemplatesAnatomy -Root $repoRoot)) {

    exit 1

} else {

    Write-Host '[OK] Repo templates anatomy-validatie (PowerShell fallback)' -ForegroundColor Green

}

$reportTpl = Join-Path $repoRoot 'docs/templates/CODEBASE_AUDIT_REPORT.md'
if ((Test-Path -LiteralPath $validateScript) -and (Test-Path -LiteralPath $reportTpl)) {
  $caOk = $false
  try {
    $null = & py -3 $validateScript $reportTpl --check-codebase-audit-claims --strict-codebase-audit-claims 2>&1
    if ($LASTEXITCODE -eq 0) { $caOk = $true }
  } catch {
    Write-Verbose 'py -3 ontbreekt voor codebase-audit template check.'
  }
  if ($caOk) {
    Write-Host '[OK] CODEBASE_AUDIT_REPORT template (strict denylist)' -ForegroundColor Green
  } else {
    Write-Host '[FAIL] CODEBASE_AUDIT_REPORT.md: codebase-audit denylist' -ForegroundColor Red
    exit 1
  }
}

Import-Module (Join-Path $repoRoot 'windows/scripts/SyncSoulSnippet.psm1') -Force

$hermesRoot = Get-HermesRoot

$profilesDir = Join-Path $hermesRoot 'profiles'

if (-not (Test-Path -LiteralPath $profilesDir)) {

    Write-Host '[SKIP] Geen runtime profiles — runtime check overgeslagen' -ForegroundColor Yellow

    exit 0

}



$allowedProfiles = Get-DomainSoulProfileNames

$failures = @()

Get-ChildItem -LiteralPath $profilesDir -Directory | Sort-Object Name | ForEach-Object {

    if ($_.Name -notin $allowedProfiles) {

        $failures += "$($_.Name): geen domeinprofiel (niet in domain_toolsets.yaml; bv. orphan analyst - map verwijderen)"

        return

    }

    $soulPath = Join-Path $_.FullName 'SOUL.md'

    if (-not (Test-Path -LiteralPath $soulPath)) {

        $failures += "$($_.Name): geen SOUL.md"

        return

    }

    $t = Get-SoulFileContent -Path $soulPath

    $failures += Test-SoulAnatomyContent -Content $t -Label $_.Name

}



if ($failures.Count -gt 0) {

    foreach ($f in $failures) { Write-Host ('[FAIL] ' + $f) -ForegroundColor Red }

    Write-Host '[ACTION] windows\APPLY_SOUL_ANATOMY_RUNTIME.bat of windows\SYNC_SOUL_SNIPPETS.bat -Force' -ForegroundColor Yellow

    exit 1

}



$soulCount = @($allowedProfiles | Where-Object {

    Test-Path -LiteralPath (Join-Path $profilesDir "$_\SOUL.md")

}).Count

Write-Host ('[OK] ' + 'Runtime anatomy op ' + $soulCount + ' domeinprofiel(en) (van ' + $($allowedProfiles.Count) + ' verwacht)') -ForegroundColor Green

exit 0

