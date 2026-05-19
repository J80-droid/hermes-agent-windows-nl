# Kopieert lokale Hermes-bestanden van de repo-map naar
# %USERPROFILE%\.hermes\_local_assets\ na Hermes-backup of na git reset.
#
# Gebruik: powershell -NoProfile -ExecutionPolicy Bypass -File "windows\sync_local_assets_to_backup.ps1"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$leaf = Split-Path -Leaf $scriptDir
if ($leaf -eq 'windows') {
    $parent = Join-Path $scriptDir '..'
    $SourceDir = (Resolve-Path -LiteralPath $parent).Path
} else {
    $SourceDir = $scriptDir
}
$WinScripts = Join-Path $SourceDir 'windows'
$DestDir = Join-Path $env:USERPROFILE '.hermes\_local_assets'

New-Item -ItemType Directory -Path $DestDir -Force | Out-Null

. (Join-Path $WinScripts 'HermesIconGeneratorInvoke.ps1')

# Icoonset uit PNG (origineel + kleuren) zodat hermes_logo.ico = pixel-art, niet oud synthetisch H
$icoGen = Join-Path $WinScripts 'tools\generate_colored_hermes_icons.py'
$pngHero = Join-Path $SourceDir 'assets\Hermes_logo.png'
$pngHeroAlt = Join-Path $SourceDir 'assets\hermes_logo.png'
$pngOk = (Test-Path -LiteralPath $pngHero) -or (Test-Path -LiteralPath $pngHeroAlt)
if ((Test-Path -LiteralPath $icoGen) -and $pngOk -and (Test-HermesWindowsIconRegenNeeded -RepoRoot $SourceDir -WindowsDir $WinScripts)) {
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

# Altijd vijf taakbalk-.lnk in repo\windows\ (o.a. Start Hermes + RAG ingest), daarna mee-kopiëren naar _local_assets
$taskbarPs1 = Join-Path $WinScripts 'create_taskbar_shortcuts.ps1'
if (Test-Path -LiteralPath $taskbarPs1) {
    Write-Host -ForegroundColor Gray '  Taakbalk-.lnk vernieuwen in windows\ ...'
    & powershell -NoProfile -ExecutionPolicy Bypass -File $taskbarPs1 -RepoRoot $SourceDir -OutDir $WinScripts -Quiet
}

$files = @(
    'start_hermes.bat',
    'start_hermes_split.bat',
    'launch_hermes.bat',
    'MANAGE_BACKUPS.bat',
    'RESTORE_FROM_BACKUP.bat',
    'UPDATE_HERMES.bat',
    'APPLY_TEAM_DISPLAY.bat',
    'SETUP_HERMES.bat',
    'HERMES_SETUP_WIZARD.bat',
    'DOCTOR_FIX.bat',
    'CREATE_DESKTOP_SHORTCUT.bat',
    'REFRESH_TASKBAR_SHORTCUTS.bat',
    'reset_hermes_memory.bat',
    'setup_hermes_windows.ps1',
    'run_hermes.ps1',
    'backup_hermes.ps1',
    'restore_from_backup.ps1',
    'apply_team_display.ps1',
    'team_display.defaults',
    'SKIP_TEAM_DISPLAY_AFTER_UPDATE.example',
    'create_shortcut.ps1',
    'create_taskbar_shortcuts.ps1',
    'launcher_config.ps1',
    'HermesIconGeneratorInvoke.ps1',
    'find_tools_registry.ps1',
    'Invoke-HermesPSScriptAnalyzer.ps1',
    'PSScriptAnalyzerSettings.psd1',
    'hermes_logo.ico',
    'hermes_logo_backup.ico',
    'hermes_logo_restore.ico',
    'hermes_logo_update.ico',
    'restore_local_assets.bat',
    'restore_local_assets.ps1',
    'sync_local_assets_to_backup.ps1',
    'README.md',
    'DELEN_MET_VRIENDEN.md',
    'Start Hermes - naar taakbalk slepen.lnk',
    'Hermes - backup - naar taakbalk slepen.lnk',
    'Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk',
    'Hermes - update - naar taakbalk slepen.lnk',
    'Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk'
)

Write-Host -ForegroundColor Yellow ('Synchroniseren: repo-root + windows\ naar ' + $DestDir + ' ...')
foreach ($file in $files) {
    if ($file -eq 'start_hermes.bat' -or $file -eq 'start_hermes_split.bat') {
        $src = Join-Path $SourceDir $file
    } else {
        $src = Join-Path $WinScripts $file
    }
    $dst = Join-Path $DestDir $file
    if (Test-Path -LiteralPath $src) {
        Copy-Item -LiteralPath $src -Destination $dst -Force
        $okLine = '  OK  ' + $file
        Write-Host -ForegroundColor Green $okLine
    } else {
        $skipLine = '  SKIP  ' + $file + ' - niet in repo'
        Write-Host -ForegroundColor DarkYellow $skipLine
    }
}

# Submappen windows\tests en windows\audits (runners + README)
$bundles = @(
    @{ Sub = 'tests'; Files = @('RUN_PYTEST.ps1', 'RUN_PSScriptAnalyzer.ps1', 'README.md', 'RUN_PYTEST.bat', 'RUN_PSScriptAnalyzer.bat') },
    @{ Sub = 'audits'; Files = @('RUN_AUDITS.ps1', 'README.md', 'RUN_AUDITS.bat', 'TY_UPSTREAM_NOTES.md', 'Install-PSScriptAnalyzer.ps1') },
    @{ Sub = 'tools'; Files = @('generate_colored_hermes_icons.py') },
    @{ Sub = 'scripts'; Files = @('update_knowledge.bat') }
)
foreach ($b in $bundles) {
    $destSub = Join-Path $DestDir $b.Sub
    New-Item -ItemType Directory -Path $destSub -Force | Out-Null
    foreach ($f in $b.Files) {
        $src = Join-Path $WinScripts (Join-Path $b.Sub $f)
        $dst = Join-Path $destSub $f
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination $dst -Force
            Write-Host -ForegroundColor Green ('  OK  ' + $b.Sub + '\' + $f)
        } else {
            Write-Host -ForegroundColor DarkYellow ('  SKIP  ' + $b.Sub + '\' + $f + ' - niet in repo')
        }
    }
}

# Repo-root assets (o.a. Hermes_logo.png voor generate_colored_hermes_icons.py)
$repoAssets = Join-Path $SourceDir 'assets'
$assetMirrorFiles = @('Hermes_logo.png', 'hermes_logo.png', 'banner.png')
$destAssets = Join-Path $DestDir 'assets'
if (Test-Path -LiteralPath $repoAssets) {
    New-Item -ItemType Directory -Path $destAssets -Force | Out-Null
    foreach ($af in $assetMirrorFiles) {
        $srcA = Join-Path $repoAssets $af
        if (Test-Path -LiteralPath $srcA) {
            $dstA = Join-Path $destAssets $af
            Copy-Item -LiteralPath $srcA -Destination $dstA -Force
            Write-Host -ForegroundColor Green ('  OK  assets\' + $af)
        }
    }
}

Write-Host 'Klaar.' -ForegroundColor Cyan
