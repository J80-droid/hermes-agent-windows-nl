# Hermes Agent: taakbalk-snelkoppelingen (.lnk) in een doelmap (zelfde set als bij backup).
# Standaarddoel: deze map (windows\) zodat gebruikers ze naar de taakbalk kunnen slepen.
param(
    [string]$RepoRoot = '',
    [string]$OutDir = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'HermesShellCommon.ps1')

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
$icoGenPy = Join-HermesRepoPath -RepoRoot $windowsDirResolved -RelativePath 'tools/generate_colored_hermes_icons.py'
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
    'Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk',
    'Hermes - Obsidian vault - naar taakbalk slepen.lnk'
)
$shortcutBats = @(
    $startHermesRel,
    'windows/SETUP_HERMES.bat',
    'windows/MANAGE_BACKUPS.bat',
    'windows/restore_local_assets.bat',
    'windows/UPDATE_HERMES.bat',
    'windows/RAG_KNOWLEDGE_UPDATE.bat',
    'windows/OPEN_OBSIDIAN_VAULT.bat'
)
$shortcutRoles = @('Start', 'Setup', 'Backup', 'Restore', 'Update', 'Rag', 'Obsidian')
$shortcutDescriptions = @(
    $startHermesDesc,
    'Hermes: Windows-setup (SETUP_HERMES.bat) - sleep naar taakbalk',
    'Hermes: fysieke backup uitvoeren (sleep naar taakbalk)',
    'Hermes: lokale scripts uit _local_assets herstellen (sleep naar taakbalk)',
    'Hermes: git/pip update via conda (sleep naar taakbalk)',
    'Hermes RAG: interactief (J/N + pause) - sleep naar taakbalk. Nacht: RAG_KNOWLEDGE_UPDATE_NIGHT.bat',
    'Hermes Knowledge (Obsidian L4): env-sync, scaffold, open vault - sleep naar taakbalk'
)
$shortcutKeepOpen = @($false, $false, $false, $false, $false, $true, $false)

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
    $batPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $shortcutBats[$shortcutIndex]
    $iconPath = Get-HermesTaskbarRoleIconPath -Role $shortcutRoles[$shortcutIndex] -WindowsDir $windowsDirResolved
    try {
        $setOk = if ($shortcutRoles[$shortcutIndex] -eq 'Start') {
            Set-HermesStartShellShortcut -ShortcutPath $lnkPath -RepoRoot $RepoRoot `
                -IconIcoPath $iconPath -Description $shortcutDescriptions[$shortcutIndex]
        } else {
            Set-HermesShellShortcut -ShortcutPath $lnkPath -TargetBatPath $batPath `
                -IconIcoPath $iconPath -WorkingDirectory $RepoRoot `
                -Description $shortcutDescriptions[$shortcutIndex] `
                -KeepCmdWindowOpen:$shortcutKeepOpen[$shortcutIndex]
        }
        if ($setOk) {
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
