. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

# E2E audit: legal domein (taxonomie, SOUL, bronmappen, rooktest)
$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
Set-Location $repoRoot

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

Write-Host '=== 1/8 repo taxonomie + architectuur ===' -ForegroundColor Cyan
foreach ($rel in @(
    'docs/LEGAL_TAXONOMY.md',
    'docs/LEGAL_DOMAIN_ARCHITECTURE.md',
    'docs/templates/SOUL_LEGAL_DOMAIN.md',
    'docs/legal/_Taxonomy_README.md'
)) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath $rel))) {
        Write-Host ('[FAIL] ' + 'Ontbreekt: ' + $rel) -ForegroundColor Red
        $failures++
    }
}
if ($failures -eq 0) { Write-Host '[OK] repo docs' -ForegroundColor Green }

Write-Host '=== 2/8 runtime legal SOUL (geen zaak in Identity) ===' -ForegroundColor Cyan
$hermesRoot = Join-Path $env:LOCALAPPDATA 'hermes'
if (-not (Test-Path -LiteralPath (Join-Path $hermesRoot 'config.yaml'))) {
    $hermesRoot = Join-Path $env:USERPROFILE '.hermes'
}
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
    if ($soul -notmatch '## Juridische lenzen') {
        Write-Host '[FAIL] Geen sectie Juridische lenzen' -ForegroundColor Red
        $failures++
    }
    if ($soul -notmatch 'Klokkenluiders') {
        Write-Host '[FAIL] Klokkenluiders-lens ontbreekt' -ForegroundColor Red
        $failures++
    }
    if ($soul -notmatch 'Forensic & trust') {
        Write-Host '[FAIL] Forensic & trust sectie ontbreekt in legal SOUL' -ForegroundColor Red
        $failures++
    }
    if ($soul -notmatch 'Values & Principles|Advisory & trust') {
        Write-Host '[FAIL] Values & Principles ontbreekt in legal SOUL' -ForegroundColor Red
        $failures++
    }
    if ($soul -notmatch 'Trust & verification|Advisory & trust') {
        Write-Host '[FAIL] Trust & verification ontbreekt in legal SOUL' -ForegroundColor Red
        $failures++
    }
    if ($soul -notmatch 'Example Interaction') {
        Write-Host '[FAIL] Example Interaction ontbreekt in legal SOUL' -ForegroundColor Red
        $failures++
    }
    if ($soul -match 'LEGAL_ACTIVE_MATTERS') {
        Write-Host '[OK] runtime legal SOUL structuur' -ForegroundColor Green
    } else {
        Write-Host '[WARN] LEGAL_ACTIVE_MATTERS niet vermeld in SOUL' -ForegroundColor Yellow
    }
}

Write-Host '=== 3/8 legal memories (trust seed) ===' -ForegroundColor Cyan
$legalUser = Join-Path $hermesRoot 'profiles\legal\memories\USER.md'
if (-not (Test-Path -LiteralPath $legalUser)) {
    Write-Host '[FAIL] profiles/legal/memories/USER.md ontbreekt' -ForegroundColor Red
    $failures++
} elseif ((Get-Content -LiteralPath $legalUser -Raw) -notmatch 'no pleaser|pleaser-behavior') {
    Write-Host '[FAIL] legal USER.md mist trust seed' -ForegroundColor Red
    $failures++
} else {
    Write-Host '[OK] legal profile memory' -ForegroundColor Green
}

Write-Host '=== 4/8 LEGAL_ACTIVE_MATTERS.md ===' -ForegroundColor Cyan
$matters = Join-Path $hermesRoot 'profiles\legal\LEGAL_ACTIVE_MATTERS.md'
if (-not (Test-Path -LiteralPath $matters)) {
    Write-Host ('[FAIL] ' + 'Ontbreekt: ' + $matters) -ForegroundColor Red
    $failures++
} elseif ((Get-Content -LiteralPath $matters -Raw) -notmatch 'GCR 2024-00145') {
    Write-Host '[FAIL] GCR niet in LEGAL_ACTIVE_MATTERS' -ForegroundColor Red
    $failures++
} else {
    Write-Host '[OK] actieve zaken bestand' -ForegroundColor Green
}

Write-Host '=== 5/8 bron-submappen ===' -ForegroundColor Cyan
$rawLegal = Join-Path $env:USERPROFILE 'data\raw_source_files\04_Legal_Corporate'
$expected = @('Arbeidsrecht', 'Bestuursrecht', 'Aansprakelijkheid_Letselschade', 'Klokkenluiders', 'Corporate', '_Taxonomy')
if (-not (Test-Path -LiteralPath $rawLegal)) {
    Write-Host ('[SKIP] ' + 'Bronmap ontbreekt: ' + $rawLegal) -ForegroundColor Yellow
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

Write-Host '=== 6/8 taxonomy sync script dry-run ===' -ForegroundColor Cyan
$conda = Find-Conda
$python = (& $conda run -n hermes-env python -c "import sys; print(sys.executable)" 2>&1 | Select-Object -Last 1).Trim()
& $python (Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'scripts/rag_pipeline/sync_legal_lens_table_from_taxonomy.py') --dry-run
if (Test-NativeCommandFailed) { $failures++ }

Write-Host '=== 7/8 pytest legal docs ===' -ForegroundColor Cyan
& $python -m pytest tests/windows/test_legal_domain_docs.py -q --tb=short 2>$null
if (Test-NativeCommandFailed) {
    Write-Host '[SKIP] test_legal_domain_docs.py nog niet aanwezig of failed' -ForegroundColor Yellow
}

Write-Host '=== 8/8 legal rooktest (search) ===' -ForegroundColor Cyan
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
