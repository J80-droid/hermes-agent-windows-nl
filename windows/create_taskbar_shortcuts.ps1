# Hermes Agent: taakbalk-snelkoppelingen (.lnk) in een doelmap (zelfde set als bij backup).
# Standaarddoel: deze map (windows\) zodat gebruikers ze naar de taakbalk kunnen slepen.
param(
    [string]$RepoRoot = '',
    [string]$OutDir = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } elseif ($MyInvocation.MyCommand.Path) {
    Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    (Get-Location).Path
}
. (Join-Path $scriptDir 'HermesIconGeneratorInvoke.ps1')

if (-not $RepoRoot.Trim()) {
    if ((Split-Path -Leaf $scriptDir) -ieq 'windows') {
        $RepoRoot = (Resolve-Path (Join-Path $scriptDir '..')).Path
    } else {
        Write-Host '[ERROR] Geef -RepoRoot door (map met pyproject.toml).' -ForegroundColor Red
        exit 1
    }
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}

$windowsDirResolved = Join-Path $RepoRoot 'windows'
$icoGenPy = Join-Path $windowsDirResolved 'tools/generate_colored_hermes_icons.py'
$needIconGen = (Test-Path -LiteralPath $icoGenPy) -and (
    Test-HermesWindowsIconRegenNeeded -RepoRoot $RepoRoot -WindowsDir $windowsDirResolved
)
if ($needIconGen) {
    if (-not $Quiet) {
        Write-Host '  Icoonset vernieuwen (hermes_logo.ico liep achter op PNG of gekleurde .ico) ...' -ForegroundColor Gray
    }
    [void](Invoke-HermesColoredIconsFromPng -IconGeneratorPy $icoGenPy -Quiet:$Quiet)
}
[void](Publish-HermesShortcutIconCache -WindowsDir $windowsDirResolved)

. (Join-Path $scriptDir 'launcher_config.ps1')
$startHermesRel = Get-HermesStartLauncherRelativePath -RepoRoot $RepoRoot
$startHermesDesc = if ($startHermesRel -eq 'start_hermes_split.bat') {
    'Hermes starten (start_hermes_split.bat / Windows Terminal) - sleep naar taakbalk'
} elseif ($startHermesRel -eq 'start_hermes.bat') {
    'Hermes starten (start_hermes.bat) - sleep naar taakbalk'
} else {
    "Hermes starten ($startHermesRel) - sleep naar taakbalk"
}

if (-not $OutDir.Trim()) {
    $OutDir = $scriptDir
} else {
    $OutDir = (Resolve-Path -LiteralPath $OutDir.Trim()).Path
}

if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
    $OutDir = (Resolve-Path -LiteralPath $OutDir).Path
}

$shortcutNames = @(
    'Start Hermes - naar taakbalk slepen.lnk',
    'Hermes - setup Windows - naar taakbalk slepen.lnk',
    'Hermes - backup - naar taakbalk slepen.lnk',
    'Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk',
    'Hermes - update - naar taakbalk slepen.lnk',
    'Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk'
)
$shortcutBats = @(
    $startHermesRel,
    'windows/SETUP_HERMES.bat',
    'windows/MANAGE_BACKUPS.bat',
    'windows/restore_local_assets.bat',
    'windows/UPDATE_HERMES.bat',
    'windows/RAG_KNOWLEDGE_UPDATE.bat'
)
$shortcutRoles = @('Start', 'Setup', 'Backup', 'Restore', 'Update', 'Rag')
$shortcutDescriptions = @(
    $startHermesDesc,
    'Hermes: Windows-setup (SETUP_HERMES.bat) - sleep naar taakbalk',
    'Hermes: fysieke backup uitvoeren (sleep naar taakbalk)',
    'Hermes: lokale scripts uit _local_assets herstellen (sleep naar taakbalk)',
    'Hermes: git/pip update via conda (sleep naar taakbalk)',
    'Hermes RAG: interactief (J/N + pause) - sleep naar taakbalk. Nacht: RAG_KNOWLEDGE_UPDATE_NIGHT.bat'
)
$shortcutKeepOpen = @($false, $false, $false, $false, $false, $true)

$legacyStartLnk = Join-Path $OutDir 'Hermes Agent - naar taakbalk slepen.lnk'
if (Test-Path -LiteralPath $legacyStartLnk) {
    Remove-Item -LiteralPath $legacyStartLnk -Force -ErrorAction SilentlyContinue
    if (-not $Quiet) {
        Write-Host '  [INFO] Oude snelkoppeling verwijderd: Hermes Agent - naar taakbalk slepen.lnk' -ForegroundColor DarkGray
    }
}

if (-not $Quiet) {
    Write-Host "Taakbalk-snelkoppelingen -> $OutDir" -ForegroundColor Gray
}

$shortcutPairCount = $shortcutNames.Count
for ($shortcutIndex = 0; $shortcutIndex -lt $shortcutPairCount; $shortcutIndex++) {
    $lnkPath = Join-Path $OutDir $shortcutNames[$shortcutIndex]
    $batPath = Join-Path $RepoRoot ($shortcutBats[$shortcutIndex] -replace '/', '\')
    $iconPath = Get-HermesTaskbarRoleIconPath -Role $shortcutRoles[$shortcutIndex] -WindowsDir $windowsDirResolved
    try {
        if (Set-HermesShellShortcut -ShortcutPath $lnkPath -TargetBatPath $batPath `
                -IconIcoPath $iconPath -WorkingDirectory $RepoRoot `
                -Description $shortcutDescriptions[$shortcutIndex] `
                -KeepCmdWindowOpen:$shortcutKeepOpen[$shortcutIndex]) {
            if (-not $Quiet) {
                Write-Host "  [OK] $($shortcutNames[$shortcutIndex])" -ForegroundColor Green
            }
        } else {
            if (-not $Quiet) {
                Write-Host "  [SKIP] $($shortcutNames[$shortcutIndex]) - ontbreekt: $batPath" -ForegroundColor Yellow
            }
        }
    } catch {
        if (-not $Quiet) {
            Write-Host "  [WARNING] $($shortcutNames[$shortcutIndex]): $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

if (-not $Quiet) {
    Write-Host '[OK] Klaar.' -ForegroundColor Cyan
}

exit 0
