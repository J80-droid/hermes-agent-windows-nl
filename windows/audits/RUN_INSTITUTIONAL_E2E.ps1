# E2E audit: institutioneel optimalisatiepakket (landkaart, SOUL backup/sync, templates)
$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
Set-Location $repoRoot

function Find-Conda {
    foreach ($p in @(
        (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
        (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe'),
        (Join-Path ${env:ProgramData} 'miniconda3\Scripts\conda.exe')
    )) {
        if ($p -and (Test-Path -LiteralPath $p)) { return $p }
    }
    throw 'conda.exe niet gevonden (hermes-env vereist)'
}

$conda = Find-Conda
$python = & $conda run -n hermes-env python -c "import sys; print(sys.executable)" 2>&1
if ($LASTEXITCODE -ne 0) { throw 'hermes-env python niet beschikbaar' }
$python = ($python | Select-Object -Last 1).Trim()

$requiredRepo = @(
    'docs/ORCHESTRATOR_ROUTING.md',
    'docs/LEGAL_TAXONOMY.md',
    'docs/LEGAL_DOMAIN_ARCHITECTURE.md',
    'docs/templates/SOUL_LEGAL_DOMAIN.md',
    'docs/templates/SOUL_SHARED_INTERACTION.md',
    'docs/templates/SOUL_CORE_ORCHESTRATOR.md',
    'skills/productivity/landkaart/SKILL.md',
    'skills/productivity/landkaart/scripts/inventory_landkaart.py',
    'windows/backup_soul_profiles.ps1',
    'windows/scripts/sync_soul_interaction_snippet.ps1',
    'windows/SYNC_SOUL_SNIPPETS.bat'
)

Write-Host '=== 1/6 repo-artefacten ===' -ForegroundColor Cyan
foreach ($rel in $requiredRepo) {
    $full = Join-Path $repoRoot ($rel -replace '/', '\')
    if (-not (Test-Path -LiteralPath $full)) {
        Write-Host "[FAIL] Ontbreekt: $rel" -ForegroundColor Red
        exit 1
    }
}
Write-Host "[OK] $($requiredRepo.Count) artefacten aanwezig" -ForegroundColor Green

Write-Host '=== 2/6 pytest institutioneel subset ===' -ForegroundColor Cyan
& $python -m pytest `
    tests/skills/test_landkaart_inventory.py `
    tests/windows/test_critical_windows_scripts.py::test_orchestrator_routing_doc_exists `
    tests/windows/test_critical_windows_scripts.py::test_landkaart_skill_exists `
    -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '=== 3/6 landkaart CLI smoke ===' -ForegroundColor Cyan
$landkaart = Join-Path $repoRoot 'skills/productivity/landkaart/scripts/inventory_landkaart.py'
$stdin = "alpha`nbeta`ngamma"
$jsonOut = ($stdin | & $python $landkaart --json 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] landkaart --json exit $LASTEXITCODE" -ForegroundColor Red
    Write-Host $jsonOut
    exit 1
}
try {
    $data = $jsonOut | ConvertFrom-Json
} catch {
    Write-Host "[FAIL] landkaart JSON ongeldig: $jsonOut" -ForegroundColor Red
    exit 1
}
if ($data.count -ne 3) {
    Write-Host "[FAIL] landkaart count=$($data.count) (verwacht 3)" -ForegroundColor Red
    exit 1
}
Write-Host '[OK] landkaart inventarisatie (3 items)' -ForegroundColor Green

Write-Host '=== 4/6 backup_soul_profiles (tijdelijke map) ===' -ForegroundColor Cyan
$tempBackup = Join-Path $env:TEMP ("hermes_institutional_e2e_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempBackup -Force | Out-Null
try {
    $copied = & (Join-Path $repoRoot 'windows/backup_soul_profiles.ps1') -BackupFolder $tempBackup
    if ($null -eq $copied) { $copied = @() }
    $personaRoot = Join-Path $tempBackup 'localappdata_hermes'
    if (-not (Test-Path -LiteralPath $personaRoot)) {
        Write-Host '[SKIP] Geen runtime Hermes home — backup_soul overgeslagen' -ForegroundColor Yellow
    } elseif ($copied.Count -eq 0) {
        Write-Host '[FAIL] Runtime home gevonden maar 0 persona-bestanden gekopieerd' -ForegroundColor Red
        exit 1
    } else {
        Write-Host "[OK] backup_soul: $($copied.Count) bestand(en)" -ForegroundColor Green
        $coreSoul = Join-Path $personaRoot 'profiles\core\SOUL.md'
        if (Test-Path -LiteralPath $coreSoul) {
            $coreText = Get-Content -LiteralPath $coreSoul -Raw -Encoding UTF8
            if ($coreText -notmatch 'Routing|orchestrator|landkaart') {
                Write-Host '[WARN] core SOUL mist routing/landkaart-signalen (controleer runtime)' -ForegroundColor Yellow
            }
        }
    }
} finally {
    if (Test-Path -LiteralPath $tempBackup) {
        Remove-Item -LiteralPath $tempBackup -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host '=== 5/6 SOUL Interaction (runtime read-only) ===' -ForegroundColor Cyan
$hermesRoot = Join-Path $env:LOCALAPPDATA 'hermes'
if (-not (Test-Path -LiteralPath (Join-Path $hermesRoot 'config.yaml'))) {
    $hermesRoot = Join-Path $env:USERPROFILE '.hermes'
}
$coreSoulPath = Join-Path $hermesRoot 'profiles\core\SOUL.md'
$template = Get-Content -LiteralPath (Join-Path $repoRoot 'docs/templates/SOUL_SHARED_INTERACTION.md') -Raw -Encoding UTF8
if (-not (Test-Path -LiteralPath $coreSoulPath)) {
    Write-Host "[SKIP] Geen runtime core SOUL: $coreSoulPath" -ForegroundColor Yellow
} else {
    $coreSoul = Get-Content -LiteralPath $coreSoulPath -Raw -Encoding UTF8
    if ($coreSoul -notmatch '## Interaction met J\.') {
        Write-Host '[FAIL] core SOUL mist ## Interaction met J.' -ForegroundColor Red
        exit 1
    }
    if ($template.Trim() -notmatch 'landkaart' -or $coreSoul -notmatch 'landkaart|volledige lijst') {
        Write-Host '[FAIL] Interaction/landkaart-tekst ontbreekt in template of runtime core SOUL' -ForegroundColor Red
        exit 1
    }
    Write-Host '[OK] core SOUL Interaction + landkaart aanwezig' -ForegroundColor Green
}

Write-Host '=== 6/6 RESTORE help + UPDATE skip-pause regressie ===' -ForegroundColor Cyan
$restoreBat = Join-Path $repoRoot 'windows/RESTORE_FROM_BACKUP.bat'
$restoreText = Get-Content -LiteralPath $restoreBat -Raw -Encoding UTF8
if ($restoreText -notmatch 'RestoreRuntimePersonas') {
    Write-Host '[FAIL] RESTORE_FROM_BACKUP.bat vermeldt -RestoreRuntimePersonas niet' -ForegroundColor Red
    exit 1
}
$updateBat = Get-Content -LiteralPath (Join-Path $repoRoot 'windows/UPDATE_HERMES.bat') -Raw -Encoding UTF8
if ($updateBat -notmatch 'HERMES_SKIP_PAUSE_AFTER_UPDATE') {
    Write-Host '[FAIL] UPDATE_HERMES.bat mist HERMES_SKIP_PAUSE_AFTER_UPDATE' -ForegroundColor Red
    exit 1
}
Write-Host '[OK] restore/update regressie-checks' -ForegroundColor Green

Write-Host '=== INSTITUTIONAL E2E: PASS ===' -ForegroundColor Green
exit 0
