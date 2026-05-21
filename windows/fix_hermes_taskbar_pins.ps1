# Vernieuwt Hermes-taakbalk-pins: icoon + cmd.exe-wrapper (Windows negeert IconLocation bij .bat-target).
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $RepoRoot.Trim()) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptDir '..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}

$createPs1 = Join-Path $scriptDir 'create_taskbar_shortcuts.ps1'
if (-not (Test-Path -LiteralPath $createPs1)) {
    Write-Host "[ERROR] Ontbreekt: $createPs1" -ForegroundColor Red
    exit 1
}

. (Join-Path $scriptDir 'HermesIconGeneratorInvoke.ps1')
. (Join-Path $scriptDir 'launcher_config.ps1')

& $createPs1 -RepoRoot $RepoRoot -OutDir $scriptDir -Quiet:$Quiet

$startBatRel = Get-HermesStartLauncherRelativePath -RepoRoot $RepoRoot
$startBatFull = Join-Path $RepoRoot $startBatRel

function Test-HermesTaskbarWhiteIcoStale {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $true }
    try {
        return ((Get-Item -LiteralPath $Path).Length -lt 12000)
    } catch {
        return $true
    }
}

function Resolve-HermesUpdateShortcutIcon {
    param([string]$WindowsDir)
    $white = Join-Path $WindowsDir 'hermes_taskbar_white.ico'
    if ((Test-Path -LiteralPath $white) -and -not (Test-HermesTaskbarWhiteIcoStale -Path $white)) {
        return (Get-HermesWindowsShellIcoLocation -IcoPath $white)
    }
    $orange = Join-Path $WindowsDir 'hermes_logo_update.ico'
    if (Test-Path -LiteralPath $orange) {
        return (Get-HermesWindowsShellIcoLocation -IcoPath $orange)
    }
    $main = Join-Path $WindowsDir 'hermes_logo.ico'
    if (Test-Path -LiteralPath $main) {
        return (Get-HermesWindowsShellIcoLocation -IcoPath $main)
    }
    return $null
}

function Clear-HermesShellIconCache {
    $ie4u = Join-Path $env:SystemRoot 'System32\ie4uinit.exe'
    if (-not (Test-Path -LiteralPath $ie4u)) { return }
    Start-Process -FilePath $ie4u -ArgumentList '-show' -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
    Start-Process -FilePath $ie4u -ArgumentList '-ClearIconCache' -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
}

function Repair-HermesBatShortcut {
    [CmdletBinding(SupportsShouldProcess)]
    param([string]$LnkPath, [string]$BatPath, [string]$RepoRoot, [string]$IconPath)
    if (-not (Test-Path -LiteralPath $LnkPath)) { return }
    if (-not $PSCmdlet.ShouldProcess($LnkPath, 'Update', 'Hermes shortcut')) { return }
    if (-not (Test-Path -LiteralPath $BatPath)) { return }
    $w = New-Object -ComObject WScript.Shell
    $s = $w.CreateShortcut($LnkPath)
    # Altijd cmd-wrapper + icoon zetten (ook als Target al cmd.exe is — anders blijft IconLocation ongewijzigd).
    $s.TargetPath = Join-Path $env:SystemRoot 'System32\cmd.exe'
    $s.Arguments = '/c "' + $BatPath + '"'
    $s.WorkingDirectory = $RepoRoot
    if ($IconPath) {
        if ($IconPath -match ',\d+$') {
            $s.IconLocation = $IconPath
        } elseif (Test-Path -LiteralPath $IconPath) {
            $s.IconLocation = Get-HermesWindowsShellIcoLocation -IcoPath $IconPath
        }
    }
    $s.Save()
}

$whiteIco = Join-Path $scriptDir 'hermes_taskbar_white.ico'
$updateIconLoc = Resolve-HermesUpdateShortcutIcon -WindowsDir $scriptDir

$batIconPairs = @(
    @{
        LnkLeaf  = 'Hermes - update - naar taakbalk slepen.lnk'
        BatLeaf  = 'UPDATE_HERMES.bat'
        IconPath = $updateIconLoc
    },
    @{
        LnkLeaf  = 'Hermes - setup Windows - naar taakbalk slepen.lnk'
        BatLeaf  = 'setup_hermes_windows.bat'
        IconPath = $whiteIco
    },
    @{
        LnkLeaf  = 'Start Hermes - naar taakbalk slepen.lnk'
        BatLeaf  = $startBatFull
        IconPath = (Join-Path $scriptDir 'hermes_logo.ico')
    },
    @{
        LnkLeaf  = 'Hermes - backup - naar taakbalk slepen.lnk'
        BatLeaf  = 'MANAGE_BACKUPS.bat'
        IconPath = (Join-Path $scriptDir 'hermes_logo_backup.ico')
    },
    @{
        LnkLeaf  = 'Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk'
        BatLeaf  = 'restore_local_assets.bat'
        IconPath = (Join-Path $scriptDir 'hermes_logo_restore.ico')
    },
    @{
        LnkLeaf  = 'Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk'
        BatLeaf  = 'RAG_KNOWLEDGE_UPDATE_NIGHT.bat'
        IconPath = (Join-Path $scriptDir 'hermes_logo.ico')
    }
)

foreach ($pair in $batIconPairs) {
    $lnk = Join-Path $scriptDir $pair.LnkLeaf
    if (-not (Test-Path -LiteralPath $lnk)) { continue }
    if ($pair.BatLeaf -and (Test-Path -LiteralPath $pair.BatLeaf)) {
        Repair-HermesBatShortcut -LnkPath $lnk -BatPath $pair.BatLeaf -RepoRoot $RepoRoot -IconPath $pair.IconPath
    } elseif ($pair.IconPath -and (Test-Path -LiteralPath $pair.IconPath)) {
        $w = New-Object -ComObject WScript.Shell
        $s = $w.CreateShortcut($lnk)
        $s.IconLocation = Get-HermesWindowsShellIcoLocation -IcoPath $pair.IconPath
        $s.Save()
    }
}

$openBat = Join-Path $scriptDir 'OPEN_SETUP.bat'
if (Test-Path -LiteralPath $openBat) {
    Repair-HermesBatShortcut -LnkPath (Join-Path $scriptDir 'Hermes - Open Setup - naar taakbalk slepen.lnk') `
        -BatPath $openBat -RepoRoot $RepoRoot -IconPath $whiteIco
}

function Update-PinnedHermesShortcut {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [string]$SourceLnk,
        [string]$PinnedDir
    )
    if (-not (Test-Path -LiteralPath $SourceLnk)) { return $false }
    if (-not (Test-Path -LiteralPath $PinnedDir)) { return $false }
    $name = [IO.Path]::GetFileName($SourceLnk)
    $dest = Join-Path $PinnedDir $name
    if (-not $PSCmdlet.ShouldProcess($dest, 'Update', 'Pinned taskbar shortcut')) { return $false }
    Copy-Item -LiteralPath $SourceLnk -Destination $dest -Force
    return $true
}

$pinnedDir = Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar'
$toPin = @(
    'Hermes - update - naar taakbalk slepen.lnk',
    'Hermes - setup Windows - naar taakbalk slepen.lnk',
    'Start Hermes - naar taakbalk slepen.lnk',
    'Hermes - backup - naar taakbalk slepen.lnk'
)

if (Test-Path -LiteralPath $pinnedDir) {
    foreach ($leaf in $toPin) {
        $src = Join-Path $scriptDir $leaf
        if (Update-PinnedHermesShortcut -SourceLnk $src -PinnedDir $pinnedDir) {
            if (-not $Quiet) {
                Write-Host "  [OK] Taakbalk-pin bijgewerkt: $leaf" -ForegroundColor Green
            }
        }
    }
} elseif (-not $Quiet) {
    Write-Host '  [INFO] Geen map User Pinned\TaskBar - pin handmatig via rechtsklik.' -ForegroundColor Gray
}

Clear-HermesShellIconCache

if (-not $Quiet) {
    Write-Host ''
    Write-Host 'Als UPDATE nog een zwart H toont (andere Hermes-iconen wel goed):' -ForegroundColor Cyan
    Write-Host '  1. Rechtsklik de UPDATE-pin op de taakbalk -> Losmaken van de taakbalk' -ForegroundColor Gray
    Write-Host '  2. windows\Hermes - update - naar taakbalk slepen.lnk -> rechtsklik -> Vastmaken aan taakbalk' -ForegroundColor Gray
    Write-Host '     (niet UPDATE_HERMES.bat direct slepen — dan blijft het cmd-H)' -ForegroundColor Gray
    Write-Host '  3. Icooncache is zojuist ververst (ie4uinit); anders: FIX_TASKBAR_ICONS.bat opnieuw' -ForegroundColor Gray
}

exit 0
