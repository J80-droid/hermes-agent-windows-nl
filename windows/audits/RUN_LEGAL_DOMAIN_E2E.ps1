. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

# E2E audit: legal domein (taxonomie, SOUL, bronmappen, parity, rooktest)
param(
    [switch]$StrictSources,
    [switch]$ApplyLensSync
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
Set-Location $repoRoot
$totalSteps = 12

if ($StrictSources) { $env:HERMES_LEGAL_VERIFY_STRICT = '1' }

function Find-Conda {
    foreach ($p in @(
        (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
        (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe')
    )) {
        if ($p -and (Test-Path -LiteralPath $p)) { return $p }
    }
    throw 'conda.exe niet gevonden'
}

$failures = 0
$hermesRoot = Join-Path $env:LOCALAPPDATA 'hermes'
if (-not (Test-Path -LiteralPath (Join-Path $hermesRoot 'config.yaml'))) {
    $hermesRoot = Join-Path $env:USERPROFILE '.hermes'
}

Write-Host "=== 1/$totalSteps repo taxonomie + architectuur ===" -ForegroundColor Cyan
foreach ($rel in @(
    'docs/LEGAL_TAXONOMY.md',
    'docs/LEGAL_DOMAIN_ARCHITECTURE.md',
    'docs/templates/SOUL_LEGAL_DOMAIN.md',
    'docs/legal/_Taxonomy_README.md',
    'docs/templates/LEGAL_ACTIVE_MATTERS.example.md'
)) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath $rel))) {
        Write-Host ('[FAIL] ' + 'Ontbreekt: ' + $rel) -ForegroundColor Red
        $failures++
    }
}
if ($failures -eq 0) { Write-Host '[OK] repo docs' -ForegroundColor Green }

Write-Host "=== 2/$totalSteps runtime legal SOUL ===" -ForegroundColor Cyan
$legalSoul = Join-Path $hermesRoot 'profiles\legal\SOUL.md'
if (-not (Test-Path -LiteralPath $legalSoul)) {
    Write-Host ('[FAIL] ' + 'Ontbreekt: ' + $legalSoul) -ForegroundColor Red
    $failures++
} else {
    $soul = Get-Content -LiteralPath $legalSoul -Raw -Encoding UTF8
    if ($soul -match 'GCR 2024-00145' -and $soul -match '## Identity') {
        $identityBlock = ($soul -split '(?=## Mission)', 2)[0]
        if ($identityBlock -match 'GCR 2024-00145') {
            Write-Host '[FAIL] GCR in Identity-blok (hoort in LEGAL_ACTIVE_MATTERS)' -ForegroundColor Red
            $failures++
        }
    }
    foreach ($need in @('## Juridische lenzen', 'Klokkenluiders', 'Forensic & trust', 'Example Interaction')) {
        if ($soul -notmatch [regex]::Escape($need)) {
            Write-Host "[FAIL] Ontbreekt in legal SOUL: $need" -ForegroundColor Red
            $failures++
        }
    }
    if ($soul -notmatch 'Values & Principles|Advisory & trust') {
        Write-Host '[FAIL] Values & Principles ontbreekt in legal SOUL' -ForegroundColor Red
        $failures++
    }
    if ($soul -notmatch 'Trust & verification|Advisory & trust') {
        Write-Host '[FAIL] Trust & verification ontbreekt in legal SOUL' -ForegroundColor Red
        $failures++
    }
    if ($soul -match 'LEGAL_ACTIVE_MATTERS') {
        Write-Host '[OK] runtime legal SOUL structuur' -ForegroundColor Green
    } else {
        Write-Host '[WARN] LEGAL_ACTIVE_MATTERS niet vermeld in SOUL' -ForegroundColor Yellow
    }
}

Write-Host "=== 3/$totalSteps legal memories (trust seed) ===" -ForegroundColor Cyan
$legalUser = Join-Path $hermesRoot 'profiles\legal\memories\USER.md'
if (-not (Test-Path -LiteralPath $legalUser)) {
    Write-Host '[FAIL] profiles/legal/memories/USER.md ontbreekt (SYNC_TRUST_RUNTIME.bat)' -ForegroundColor Red
    $failures++
} elseif ((Get-Content -LiteralPath $legalUser -Raw) -notmatch 'no pleaser|pleaser-behavior') {
    Write-Host '[FAIL] legal USER.md mist trust seed' -ForegroundColor Red
    $failures++
} else {
    Write-Host '[OK] legal profile memory' -ForegroundColor Green
}

Write-Host "=== 4/$totalSteps LEGAL_ACTIVE_MATTERS.md ===" -ForegroundColor Cyan
& (Join-Path $repoRoot 'windows\scripts\ensure_legal_active_matters.ps1') -RepoRoot $repoRoot -Quiet
$matters = Join-Path $hermesRoot 'profiles\legal\LEGAL_ACTIVE_MATTERS.md'
if (-not (Test-Path -LiteralPath $matters)) {
    Write-Host ('[FAIL] ' + 'Ontbreekt: ' + $matters) -ForegroundColor Red
    $failures++
} elseif (-not (Test-Path -LiteralPath $matters -PathType Leaf)) {
    Write-Host '[FAIL] LEGAL_ACTIVE_MATTERS niet leesbaar als bestand' -ForegroundColor Red
    $failures++
} elseif ((Get-Content -LiteralPath $matters -Raw) -notmatch 'GCR 2024-00145') {
    Write-Host '[FAIL] GCR niet in LEGAL_ACTIVE_MATTERS' -ForegroundColor Red
    $failures++
} else {
    Write-Host '[OK] actieve zaken bestand' -ForegroundColor Green
}

Write-Host "=== 5/$totalSteps domains.yaml (user) ===" -ForegroundColor Cyan
$domainsYaml = Join-Path $env:USERPROFILE 'data\domains.yaml'
if (-not (Test-Path -LiteralPath $domainsYaml)) {
    Write-Host ('[FAIL] ' + 'domains.yaml ontbreekt: ' + $domainsYaml) -ForegroundColor Red
    $failures++
} else {
    $dy = Get-Content -LiteralPath $domainsYaml -Raw -Encoding UTF8
    if ($dy -notmatch 'lancedb-legal' -and $dy -notmatch 'legal') {
        Write-Host '[FAIL] domains.yaml: geen legal/lancedb-legal' -ForegroundColor Red
        $failures++
    } else {
        Write-Host '[OK] domains.yaml legal' -ForegroundColor Green
    }
}

Write-Host "=== 6/$totalSteps bron-submappen ===" -ForegroundColor Cyan
$rawLegal = Join-Path $env:USERPROFILE 'data\raw_source_files\04_Legal_Corporate'
$expected = @('Arbeidsrecht', 'Bestuursrecht', 'Aansprakelijkheid_Letselschade', 'Klokkenluiders', 'Corporate', '_Taxonomy')
if (-not (Test-Path -LiteralPath $rawLegal)) {
    if ($StrictSources) {
        Write-Host ('[FAIL] ' + 'Bronmap ontbreekt: ' + $rawLegal) -ForegroundColor Red
        $failures++
    } else {
        Write-Host ('[SKIP] ' + 'Bronmap ontbreekt: ' + $rawLegal) -ForegroundColor Yellow
    }
} else {
    $subMissing = 0
    foreach ($d in $expected) {
        if (-not (Test-Path -LiteralPath (Join-Path $rawLegal $d))) {
            Write-Host ('[FAIL] ' + 'Submap ontbreekt: ' + $d) -ForegroundColor Red
            $subMissing++
        }
    }
    if ($subMissing -gt 0) { $failures += $subMissing } else { Write-Host '[OK] submappen' -ForegroundColor Green }
}

Write-Host "=== 7/$totalSteps taxonomy sync ===" -ForegroundColor Cyan
$conda = Find-Conda
$python = (& $conda run -n hermes-env python -c "import sys; print(sys.executable)" 2>&1 | Select-Object -Last 1).Trim()
$syncScript = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'scripts/rag_pipeline/sync_legal_lens_table_from_taxonomy.py'
if ($ApplyLensSync) {
    & $python $syncScript --all
} else {
    & $python $syncScript --dry-run
}
if (Test-NativeCommandFailed) { $failures++ }

Write-Host "=== 8/$totalSteps pytest legal docs ===" -ForegroundColor Cyan
& $python -m pytest tests/windows/test_legal_domain_docs.py tests/windows/test_legal_meta_contract.py -q --tb=short 2>$null
if (Test-NativeCommandFailed) {
    Write-Host '[FAIL] legal pytest' -ForegroundColor Red
    $failures++
} else {
    Write-Host '[OK] legal pytest' -ForegroundColor Green
}

Write-Host "=== 9/$totalSteps lens parity (SOUL vs taxonomie) ===" -ForegroundColor Cyan
$parity = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'scripts/rag_pipeline/verify_legal_lens_parity.py'
& $python $parity --all
if (Test-NativeCommandFailed) {
    Write-Host '[FAIL] lens parity' -ForegroundColor Red
    $failures++
} else {
    Write-Host '[OK] lens parity' -ForegroundColor Green
}

Write-Host "=== 10/$totalSteps meta-secties runtime SOUL ===" -ForegroundColor Cyan
if (Test-Path -LiteralPath $legalSoul) {
    $soul = Get-Content -LiteralPath $legalSoul -Raw -Encoding UTF8
    if ($soul -notmatch 'Domeinarchitectuur|/legal-architectuur') {
        Write-Host '[FAIL] legal SOUL: Domeinarchitectuur meta ontbreekt' -ForegroundColor Red
        $failures++
    } else {
        Write-Host '[OK] legal meta-sectie' -ForegroundColor Green
    }
}
$coreSoul = Join-Path $hermesRoot 'profiles\core\SOUL.md'
if (Test-Path -LiteralPath $coreSoul) {
    $core = Get-Content -LiteralPath $coreSoul -Raw -Encoding UTF8
    if ($core -notmatch 'Legal architectuur|/legal-architectuur') {
        Write-Host '[WARN] core SOUL: Legal architectuur meta ontbreekt' -ForegroundColor Yellow
    }
}
if ($env:HERMES_LEGAL_PHASE_3B -ne '1') {
    $klokProf = Join-Path $hermesRoot 'profiles\klokkenluiders'
    if (Test-Path -LiteralPath $klokProf) {
        Write-Host '[WARN] profiles/klokkenluiders bestaat (fase 3b niet actief)' -ForegroundColor Yellow
    }
}

Write-Host "=== 11/$totalSteps RAG bron-readiness + ingest summary ===" -ForegroundColor Cyan
$readiness = Join-Path $repoRoot 'windows\scripts\Get-RagSourceReadiness.ps1'
if (Test-Path -LiteralPath $readiness) {
    & $readiness -RepoRoot $repoRoot
    if (Test-NativeCommandFailed -and $StrictSources) { $failures++ }
}
$summaryPath = Join-Path $env:USERPROFILE 'data\lancedb\legal\rag_ingest_run_summary.json'
if (Test-Path -LiteralPath $summaryPath) {
    Write-Host "[OK] ingest summary: $summaryPath" -ForegroundColor Green
} else {
    Write-Host '[WARN] Geen rag_ingest_run_summary.json (nog geen ingest)' -ForegroundColor Yellow
}

Write-Host "=== 12/$totalSteps legal rooktest (search) ===" -ForegroundColor Cyan
$rooktest = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'scripts/rag_pipeline/_rooktest_search.py'
if (Test-Path -LiteralPath $rooktest) {
    $env:HERMES_LANCEDB_PATH = Join-Path $env:USERPROFILE 'data\lancedb\legal'
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $python $rooktest 1>$null 2>$null
    $rookCode = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($rookCode -ne 0) {
        Write-Host '[WARN] search_knowledge rooktest mislukt (lege index of geen ingest)' -ForegroundColor Yellow
    } else {
        Write-Host '[OK] rooktest search' -ForegroundColor Green
    }
} else {
    Write-Host '[SKIP] rooktest script ontbreekt' -ForegroundColor Yellow
}

Write-Host ''
if ($failures -gt 0) {
    Write-Host "LEGAL DOMAIN E2E: $failures fout(en)" -ForegroundColor Red
    exit 1
}
Write-Host '=== LEGAL DOMAIN E2E: PASS ===' -ForegroundColor Green
exit 0
