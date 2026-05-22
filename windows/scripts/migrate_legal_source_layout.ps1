# Eenmalige migratie: rechtsgebied-submappen onder 04_Legal_Corporate.
# Standaard -DryRun. Gebruik -Apply om te verplaatsen.
param(
    [switch]$Apply,
    [string]$RawRoot = ''
)

$ErrorActionPreference = 'Stop'

if (-not $RawRoot) {
    $RawRoot = Join-Path $env:USERPROFILE 'data\raw_source_files\04_Legal_Corporate'
}
$legalRoot = (Resolve-Path -LiteralPath $RawRoot -ErrorAction SilentlyContinue)
if (-not $legalRoot) {
    Write-Host "[SKIP] Bronmap ontbreekt: $RawRoot" -ForegroundColor Yellow
    exit 0
}
$legalRoot = $legalRoot.Path

$lensDirs = @(
    'Arbeidsrecht',
    'Bestuursrecht',
    'Aansprakelijkheid_Letselschade',
    'Klokkenluiders',
    'Corporate',
    '_Taxonomy'
)

foreach ($d in $lensDirs) {
    $p = Join-Path $legalRoot $d
    if (-not (Test-Path -LiteralPath $p)) {
        if ($Apply) {
            New-Item -ItemType Directory -Path $p -Force | Out-Null
            Write-Host "[OK] Aangemaakt: $d\" -ForegroundColor Green
        } else {
            Write-Host "[PLAN] Aanmaken: $d\" -ForegroundColor Cyan
        }
    }
}

$taxonomyReadme = Join-Path $legalRoot '_Taxonomy\README.md'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$repoReadme = Join-Path $repoRoot 'docs\legal\_Taxonomy_README.md'
if ($Apply -and (Test-Path -LiteralPath $repoReadme)) {
    $parent = Split-Path -Parent $taxonomyReadme
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Copy-Item -LiteralPath $repoReadme -Destination $taxonomyReadme -Force
    Write-Host '[OK] _Taxonomy\README.md gekopieerd' -ForegroundColor Green
}

# Zaak-mappen (Geschillencommissie Rijk) en lens-submappen worden niet verplaatst — alleen losse bestanden in root.

# Optioneel: losse bestanden in root -> Corporate
$rootFiles = Get-ChildItem -LiteralPath $legalRoot -File -ErrorAction SilentlyContinue
foreach ($f in $rootFiles) {
    $destDir = Join-Path $legalRoot 'Corporate'
    $dest = Join-Path $destDir $f.Name
    if ($Apply) {
        if (-not (Test-Path -LiteralPath $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        if (-not (Test-Path -LiteralPath $dest)) {
            Move-Item -LiteralPath $f.FullName -Destination $dest
            Write-Host "[OK] Verplaatst naar Corporate: $($f.Name)" -ForegroundColor Green
        }
    } else {
        Write-Host "[PLAN] Root-bestand -> Corporate: $($f.Name)" -ForegroundColor Cyan
    }
}

if (-not $Apply) {
    Write-Host ''
    Write-Host 'Dry-run voltooid. Voer uit met -Apply om wijzigingen door te voeren.' -ForegroundColor Yellow
    exit 0
}

Write-Host ''
Write-Host '[OK] Legal bronlayout migratie toegepast.' -ForegroundColor Green
Write-Host 'Volgende stap: windows/scripts/update_knowledge.bat legal' -ForegroundColor Cyan
exit 0
