# Kopieert lokale Hermes-bestanden van de repo-map naar
# %USERPROFILE%\.hermes\_local_assets\ na Hermes-backup of na git reset.
#
# Paden: zie WindowsLocalAssetsManifest.ps1 (enige bron van waarheid).
# Gebruik: powershell -NoProfile -ExecutionPolicy Bypass -File "windows\sync_local_assets_to_backup.ps1"

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'WindowsLocalAssetsManifest.ps1')
. (Join-Path $PSScriptRoot 'HermesIconGeneratorInvoke.ps1')

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$leaf = Split-Path -Leaf $scriptDir
if ($leaf -eq 'windows') {
    $repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir '..')).Path
    $winDir = $scriptDir
} else {
    $repoRoot = $scriptDir
    $winDir = Join-Path $scriptDir 'windows'
}

$destDir = Join-Path $env:USERPROFILE '.hermes\_local_assets'

# Icoonset uit PNG (optioneel)
$icoGen = Join-Path $winDir 'tools\generate_colored_hermes_icons.py'
$pngHero = Join-Path $repoRoot 'assets\Hermes_logo.png'
$pngHeroAlt = Join-Path $repoRoot 'assets\hermes_logo.png'
$pngOk = (Test-Path -LiteralPath $pngHero) -or (Test-Path -LiteralPath $pngHeroAlt)
if ((Test-Path -LiteralPath $icoGen) -and $pngOk -and (Test-HermesWindowsIconRegenNeeded -RepoRoot $repoRoot -WindowsDir $winDir)) {
    Write-Host -ForegroundColor Gray '  Icoonset vernieuwen (assets PNG -> windows\*.ico) ...'
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        [void](Invoke-HermesColoredIconsFromPng -IconGeneratorPy $icoGen)
    } catch {
        Write-Host -ForegroundColor Yellow ('  [WARN] Icoon-generator: ' + $_.Exception.Message)
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

$taskbarPs1 = Join-Path $winDir 'create_taskbar_shortcuts.ps1'
if (Test-Path -LiteralPath $taskbarPs1) {
    Write-Host -ForegroundColor Gray '  Taakbalk-.lnk vernieuwen in windows\ ...'
    & powershell -NoProfile -ExecutionPolicy Bypass -File $taskbarPs1 -RepoRoot $repoRoot -OutDir $winDir -Quiet
}

Write-Host -ForegroundColor Yellow ('Synchroniseren: repo-root + windows\ (+ scripts/tests) naar ' + $destDir + ' ...')
Sync-HermesLocalAssetsFromRepo -RepoRoot $repoRoot -WindowsDir $winDir -DestDir $destDir
Write-Host 'Klaar.' -ForegroundColor Cyan
