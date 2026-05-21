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

function Resolve-HermesShortcutIconLocation {
    param([string]$IconSpec, [string]$RepoRoot)
    if ([string]::IsNullOrWhiteSpace($IconSpec)) {
        $ico = Join-Path $RepoRoot "windows\hermes_logo.ico"
        if (-not (Test-Path -LiteralPath $ico)) {
            $ico = Join-Path $RepoRoot "hermes_logo.ico"
        }
        if (Test-Path -LiteralPath $ico) {
            return (Get-HermesWindowsShellIcoLocation -IcoPath $ico)
        }
        return "cmd.exe"
    }
    if ($IconSpec -match '^(.+),(-?\d+)$') {
        $dll = $matches[1].Trim()
        if (Test-Path -LiteralPath $dll) { return $IconSpec }
    }
    if (Test-Path -LiteralPath $IconSpec) {
        if ($IconSpec -match '\.ico$') {
            return (Get-HermesWindowsShellIcoLocation -IcoPath $IconSpec)
        }
        return $IconSpec
    }
    return "cmd.exe"
}

function New-HermesTaskbarShortcut {
    param(
        [Parameter(Mandatory)][string]$ShortcutPath,
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$LaunchBatPath,
        [Parameter(Mandatory)][string]$Description,
        [Parameter(Mandatory)][string]$IconSpec
    )
    if (-not (Test-Path -LiteralPath $LaunchBatPath)) { return $false }
    $iconLoc = Resolve-HermesShortcutIconLocation -IconSpec $IconSpec -RepoRoot $RepoRoot
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    # .bat direct als target: taakbalk-pin werkt; cmd.exe /c pindt alleen "Opdrachtprompt".
    if ($LaunchBatPath -match '\.bat$') {
        $Shortcut.TargetPath = $LaunchBatPath
        $Shortcut.Arguments = ''
    } else {
        $Shortcut.TargetPath = 'cmd.exe'
        $Shortcut.Arguments = "/c `"$LaunchBatPath`""
    }
    $Shortcut.WorkingDirectory = $RepoRoot
    $Shortcut.IconLocation = $iconLoc
    $Shortcut.Description = $Description
    $Shortcut.Save()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($Shortcut) | Out-Null
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($WshShell) | Out-Null
    return $true
}

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
$whiteIco = Join-Path $windowsDirResolved 'hermes_taskbar_white.ico'
$updateIcon = if (Test-Path -LiteralPath $whiteIco) {
    $whiteIco
} else {
    (Join-Path $RepoRoot 'windows\hermes_logo_update.ico')
}
$icoGenPy = Join-Path $windowsDirResolved 'tools\generate_colored_hermes_icons.py'
if ((Test-Path -LiteralPath $icoGenPy) -and (Test-HermesWindowsIconRegenNeeded -RepoRoot $RepoRoot -WindowsDir $windowsDirResolved)) {
    if (-not $Quiet) {
        Write-Host '  Icoonset vernieuwen (hermes_logo.ico liep achter op PNG of gekleurde .ico) ...' -ForegroundColor Gray
    }
    [void](Invoke-HermesColoredIconsFromPng -IconGeneratorPy $icoGenPy -Quiet:$Quiet)
}

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
    "Start Hermes - naar taakbalk slepen.lnk",
    "Hermes - backup - naar taakbalk slepen.lnk",
    "Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk",
    "Hermes - update - naar taakbalk slepen.lnk",
    "Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk"
)
$shortcutBats = @(
    $startHermesRel,
    "windows\MANAGE_BACKUPS.bat",
    "windows\restore_local_assets.bat",
    "windows\UPDATE_HERMES.bat",
    "windows\RAG_KNOWLEDGE_UPDATE.bat"
)
$shortcutDescriptions = @(
    $startHermesDesc,
    "Hermes: fysieke backup uitvoeren (sleep naar taakbalk)",
    "Hermes: lokale scripts uit _local_assets herstellen (sleep naar taakbalk)",
    "Hermes: git/pip update via conda (sleep naar taakbalk)",
    "Hermes RAG: J=fris / N=incrementeel, alle domeinen - sleep naar taakbalk"
)
$shortcutIcons = @(
    (Join-Path $RepoRoot "windows\hermes_logo.ico"),
    (Join-Path $RepoRoot "windows\hermes_logo_backup.ico"),
    (Join-Path $RepoRoot "windows\hermes_logo_restore.ico"),
    $updateIcon,
    (Join-Path $RepoRoot "windows\hermes_logo.ico")
)

# Oude bestandsnaam was onduidelijk ("Hermes Agent"); verwijderen om dubbels te vermijden.
$legacyStartLnk = Join-Path $OutDir "Hermes Agent - naar taakbalk slepen.lnk"
if (Test-Path -LiteralPath $legacyStartLnk) {
    Remove-Item -LiteralPath $legacyStartLnk -Force -ErrorAction SilentlyContinue
    if (-not $Quiet) {
        Write-Host "  [INFO] Oude snelkoppeling verwijderd: Hermes Agent - naar taakbalk slepen.lnk" -ForegroundColor DarkGray
    }
}

if (-not $Quiet) {
    Write-Host "Taakbalk-snelkoppelingen -> $OutDir" -ForegroundColor Gray
}

$shortcutPairCount = $shortcutNames.Count
for ($shortcutIndex = 0; $shortcutIndex -lt $shortcutPairCount; $shortcutIndex++) {
    $lnkPath = Join-Path $OutDir $shortcutNames[$shortcutIndex]
    $batPath = Join-Path $RepoRoot $shortcutBats[$shortcutIndex]
    try {
        if (New-HermesTaskbarShortcut -ShortcutPath $lnkPath -RepoRoot $RepoRoot -LaunchBatPath $batPath -Description $shortcutDescriptions[$shortcutIndex] -IconSpec $shortcutIcons[$shortcutIndex]) {
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
