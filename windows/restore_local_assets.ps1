# Hermes Agent - Local Assets Restore Script
# Kopieert bestanden van %USERPROFILE%\.hermes\_local_assets naar repo (manifest).
#
# Gebruik: powershell -NoProfile -ExecutionPolicy Bypass -File "windows\restore_local_assets.ps1"

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'WindowsLocalAssetsManifest.ps1')

$localAssets = Join-Path $env:USERPROFILE '.hermes\_local_assets'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$leaf = Split-Path -Leaf $scriptDir
if ($leaf -eq 'windows') {
    $repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir '..')).Path
    $winDir = $scriptDir
} else {
    $repoRoot = $scriptDir
    $winDir = Join-Path $scriptDir 'windows'
}

if (-not (Test-Path -LiteralPath $localAssets)) {
    Write-Host -ForegroundColor Red ('FOUT: Geen lokale backup in ' + $localAssets)
    Write-Host 'Voer eerst MANAGE_BACKUPS.bat uit of git pull.'
    pause
    exit 1
}

Write-Host -ForegroundColor Magenta '===================================================='
Write-Host -ForegroundColor Magenta ' Hermes Agent - Herstellen lokale bestanden'
Write-Host -ForegroundColor DarkGray (' Van: ' + $localAssets)
Write-Host -ForegroundColor DarkGray (' Naar: ' + $repoRoot)
Write-Host -ForegroundColor Magenta '===================================================='
Write-Host ''

$result = Restore-HermesLocalAssetsToRepo -RepoRoot $repoRoot -WindowsDir $winDir -AssetsDir $localAssets

# Legacy: rag_ingest_perf_defaults.ps1 stond soms alleen in windows\ (fout pad)
$legacyPerf = Join-Path $localAssets 'rag_ingest_perf_defaults.ps1'
$canonicalPerf = Join-Path $winDir 'scripts\rag_ingest_perf_defaults.ps1'
if ((Test-Path -LiteralPath $legacyPerf) -and -not (Test-Path -LiteralPath $canonicalPerf)) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $canonicalPerf) -Force | Out-Null
    Copy-Item -LiteralPath $legacyPerf -Destination $canonicalPerf -Force
    Write-Host -ForegroundColor Green '  OK  scripts\rag_ingest_perf_defaults.ps1 (legacy migratie)'
    $result.Restored++
}

$localAssetsDir = Join-Path $localAssets 'assets'
$targetAssets = Join-Path $repoRoot 'assets'
if (Test-Path -LiteralPath $localAssetsDir) {
    New-Item -ItemType Directory -Path $targetAssets -Force | Out-Null
    foreach ($child in Get-ChildItem -LiteralPath $localAssetsDir -File -ErrorAction SilentlyContinue) {
        Copy-Item -LiteralPath $child.FullName -Destination (Join-Path $targetAssets $child.Name) -Force
        Write-Host -ForegroundColor Green ('  OK  assets\' + $child.Name)
        $result.Restored++
    }
}

Write-Host ''
Write-Host -ForegroundColor Cyan ('Klaar: ' + $result.Restored + ' hersteld, ' + $result.Skipped + ' overgeslagen')
pause
