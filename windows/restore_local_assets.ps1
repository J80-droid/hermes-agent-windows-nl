# Hermes Agent - Local Assets Restore Script
# Kopieert bestanden van %USERPROFILE%\.hermes\_local_assets naar repo-root voor start_hermes_split.bat / start_hermes.bat
# en naar repo\windows\ voor overige scripts. Byte-exact.
#
# Gebruik: powershell -NoProfile -ExecutionPolicy Bypass -File "windows\restore_local_assets.ps1"

$LocalAssets = Join-Path $env:USERPROFILE '.hermes\_local_assets'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$leaf = Split-Path -Leaf $scriptDir
if ($leaf -eq 'windows') {
    $parent = Join-Path $scriptDir '..'
    $TargetDir = (Resolve-Path -LiteralPath $parent).Path
} else {
    $TargetDir = $scriptDir
}
$windowsDir = Join-Path $TargetDir 'windows'

$assetExists = Test-Path -LiteralPath $LocalAssets
if (-not $assetExists) {
    $errMsg = 'FOUT: Geen lokale backup gevonden in ' + $LocalAssets
    Write-Host -ForegroundColor Red $errMsg
    Write-Host 'Voer eerst een Hermes-backup uit of kopieer handmatig bestanden naar die map.'
    pause
    exit 1
}

New-Item -ItemType Directory -Path $windowsDir -Force | Out-Null

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

Write-Host -ForegroundColor Magenta '===================================================='
Write-Host -ForegroundColor Magenta ' Hermes Agent - Herstellen lokale bestanden'
Write-Host -ForegroundColor DarkGray (' Van: ' + $LocalAssets)
$naarMsg = ' Naar: ' + $TargetDir + ' repo-root + ' + $windowsDir + ' windows-map'
Write-Host -ForegroundColor DarkGray $naarMsg
Write-Host -ForegroundColor Magenta '===================================================='
Write-Host ""

$restored = 0
$skipped = 0

foreach ($file in $files) {
    $src = Join-Path $LocalAssets $file
    if ($file -eq 'start_hermes.bat' -or $file -eq 'start_hermes_split.bat') {
        $dst = Join-Path $TargetDir $file
    } else {
        $dst = Join-Path $windowsDir $file
    }
    if (Test-Path -LiteralPath $src) {
        Copy-Item -LiteralPath $src -Destination $dst -Force
        $okLine = '  OK  ' + $file
        Write-Host -ForegroundColor Green $okLine
        $restored++
    } else {
        $skipLine = '  SKIP  ' + $file + ' - niet in backup'
        Write-Host -ForegroundColor DarkYellow $skipLine
        $skipped++
    }
}

$bundles = @(
    @{ Sub = 'tests'; Files = @('RUN_PYTEST.ps1', 'RUN_PSScriptAnalyzer.ps1', 'README.md', 'RUN_PYTEST.bat', 'RUN_PSScriptAnalyzer.bat') },
    @{ Sub = 'audits'; Files = @('RUN_AUDITS.ps1', 'README.md', 'RUN_AUDITS.bat', 'TY_UPSTREAM_NOTES.md', 'Install-PSScriptAnalyzer.ps1') },
    @{ Sub = 'tools'; Files = @('generate_colored_hermes_icons.py') },
    @{ Sub = 'scripts'; Files = @('update_knowledge.bat') }
)
foreach ($b in $bundles) {
    $winSub = Join-Path $windowsDir $b.Sub
    New-Item -ItemType Directory -Path $winSub -Force | Out-Null
    foreach ($f in $b.Files) {
        $src = Join-Path (Join-Path $LocalAssets $b.Sub) $f
        $dst = Join-Path $winSub $f
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination $dst -Force
            Write-Host -ForegroundColor Green ('  OK  ' + $b.Sub + '\' + $f)
            $restored++
        } else {
            Write-Host -ForegroundColor DarkYellow ('  SKIP  ' + $b.Sub + '\' + $f + ' - niet in backup')
            $skipped++
        }
    }
}

# Herstel repo-root assets\ (na sync na backup: Hermes_logo.png enz.)
$localAssetsDir = Join-Path $LocalAssets 'assets'
$targetAssets = Join-Path $TargetDir 'assets'
if (Test-Path -LiteralPath $localAssetsDir) {
    New-Item -ItemType Directory -Path $targetAssets -Force | Out-Null
    foreach ($child in Get-ChildItem -LiteralPath $localAssetsDir -File -ErrorAction SilentlyContinue) {
        $dstA = Join-Path $targetAssets $child.Name
        Copy-Item -LiteralPath $child.FullName -Destination $dstA -Force
        Write-Host -ForegroundColor Green ('  OK  assets\' + $child.Name)
        $restored++
    }
}

Write-Host ""
$klaarMsg = 'Klaar: ' + $restored + ' hersteld, ' + $skipped + ' overgeslagen'
Write-Host -ForegroundColor Cyan $klaarMsg
pause
