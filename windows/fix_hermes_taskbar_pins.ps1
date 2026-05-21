#requires -Version 5.1
# Vernieuwt Hermes-taakbalk-pins: cmd.exe-wrapper + gekleurde .ico (geen hermes_taskbar_white in .lnk).
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

. (Join-Path $scriptDir 'HermesIconGeneratorInvoke.ps1')
. (Join-Path $scriptDir 'launcher_config.ps1')

function Clear-HermesShellIconCache {
    $ie4u = Join-Path $env:SystemRoot 'System32/ie4uinit.exe'
    if (Test-Path -LiteralPath $ie4u) {
        Start-Process -FilePath $ie4u -ArgumentList '-show' -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
        Start-Process -FilePath $ie4u -ArgumentList '-ClearIconCache' -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
    }
    try {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class HermesShellNotify {
    [DllImport("shell32.dll")]
    public static extern void SHChangeNotify(int eventId, uint flags, IntPtr item1, IntPtr item2);
    public static void AssocChanged() { SHChangeNotify(0x08000000, 0x00001000, IntPtr.Zero, IntPtr.Zero); }
}
'@ -ErrorAction Stop
        [HermesShellNotify]::AssocChanged()
    } catch {
        $null = $_.Exception.Message
    }
}

function Remove-HermesTaskbarShortcutFiles {
    [CmdletBinding(SupportsShouldProcess)]
    param([Parameter(Mandatory)][string]$Dir)
    $names = @(
        'Start Hermes - naar taakbalk slepen.lnk',
        'Hermes - setup Windows - naar taakbalk slepen.lnk',
        'Hermes - backup - naar taakbalk slepen.lnk',
        'Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk',
        'Hermes - update - naar taakbalk slepen.lnk',
        'Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk',
        'Hermes - Open Setup - naar taakbalk slepen.lnk'
    )
    foreach ($leaf in $names) {
        $p = Join-Path $Dir $leaf
        if ((Test-Path -LiteralPath $p) -and $PSCmdlet.ShouldProcess($p, 'Remove', 'Taskbar shortcut')) {
            Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
        }
    }
}

function Repair-HermesBatShortcut {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [string]$LnkPath,
        [string]$BatPath,
        [string]$RepoRoot,
        [string]$IconLocation
    )
    if (-not (Test-Path -LiteralPath $LnkPath)) { return }
    if (-not $PSCmdlet.ShouldProcess($LnkPath, 'Update', 'Hermes shortcut')) { return }
    if (-not (Test-Path -LiteralPath $BatPath)) { return }
    $w = New-Object -ComObject WScript.Shell
    $s = $w.CreateShortcut($LnkPath)
    $s.TargetPath = Join-Path $env:SystemRoot 'System32/cmd.exe'
    $s.Arguments = '/c "' + $BatPath + '"'
    $s.WorkingDirectory = $RepoRoot
    if ($IconLocation) { $s.IconLocation = $IconLocation }
    $s.Save()
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

$createPs1 = Join-Path $scriptDir 'create_taskbar_shortcuts.ps1'
if (-not (Test-Path -LiteralPath $createPs1)) {
    Write-Host "[ERROR] Ontbreekt: $createPs1" -ForegroundColor Red
    exit 1
}

$icoGenPy = Join-Path $scriptDir (Join-Path 'tools' 'generate_colored_hermes_icons.py')
if (Test-Path -LiteralPath $icoGenPy) {
    if (-not $Quiet) {
        Write-Host '[INFO] Icoonset opnieuw genereren (alle groottes voor .lnk)...' -ForegroundColor Gray
    }
    [void](Invoke-HermesColoredIconsFromPng -IconGeneratorPy $icoGenPy -Quiet)
}

Remove-HermesTaskbarShortcutFiles -Dir $scriptDir
& $createPs1 -RepoRoot $RepoRoot -OutDir $scriptDir -Quiet:$Quiet

$startBatFull = Join-Path $RepoRoot (Get-HermesStartLauncherRelativePath -RepoRoot $RepoRoot)

$repairRows = @(
    , @('Hermes - update - naar taakbalk slepen.lnk', 'UPDATE_HERMES.bat', 'Update')
    , @('Hermes - setup Windows - naar taakbalk slepen.lnk', 'setup_hermes_windows.bat', 'Setup')
    , @('Start Hermes - naar taakbalk slepen.lnk', '', 'Start')
    , @('Hermes - backup - naar taakbalk slepen.lnk', 'MANAGE_BACKUPS.bat', 'Backup')
    , @('Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk', 'restore_local_assets.bat', 'Restore')
    , @('Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk', 'RAG_KNOWLEDGE_UPDATE_NIGHT.bat', 'Rag')
)

foreach ($row in $repairRows) {
    $lnk = Join-Path $scriptDir $row[0]
    if (-not (Test-Path -LiteralPath $lnk)) { continue }
    $batPath = if ($row[1]) { Join-Path $scriptDir $row[1] } else { $startBatFull }
    if (-not (Test-Path -LiteralPath $batPath)) { continue }
    $iconLoc = Get-HermesTaskbarRoleIconLocation -Role $row[2] -WindowsDir $scriptDir
    Repair-HermesBatShortcut -LnkPath $lnk -BatPath $batPath -RepoRoot $RepoRoot -IconLocation $iconLoc
}

$openBat = Join-Path $scriptDir 'OPEN_SETUP.bat'
if (Test-Path -LiteralPath $openBat) {
    $openIcon = Get-HermesTaskbarRoleIconLocation -Role 'OpenSetup' -WindowsDir $scriptDir
    Repair-HermesBatShortcut -LnkPath (Join-Path $scriptDir 'Hermes - Open Setup - naar taakbalk slepen.lnk') `
        -BatPath $openBat -RepoRoot $RepoRoot -IconLocation $openIcon
}

$pinnedDir = Join-Path $env:APPDATA (Join-Path 'Microsoft' (Join-Path 'Internet Explorer' (Join-Path 'Quick Launch' (Join-Path 'User Pinned' 'TaskBar'))))
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
    Write-Host '  [INFO] Geen map User Pinned/TaskBar - pin handmatig via rechtsklik.' -ForegroundColor Gray
}

Clear-HermesShellIconCache

if (-not $Quiet) {
    Write-Host ''
    Write-Host 'Iconen: start/RAG=goud | setup=groen | update=wit | backup=roze | restore=cyaan' -ForegroundColor Cyan
    Write-Host 'Blijft een oud H zichtbaar: pin losmaken, .lnk opnieuw vastmaken (niet .bat slepen).' -ForegroundColor Gray
}

exit 0
