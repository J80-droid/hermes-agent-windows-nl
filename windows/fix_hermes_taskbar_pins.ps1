#requires -Version 5.1
# Vernieuwt Hermes-taakbalk-.lnk (bat+ico in windows\) en taakbalk-pins (cmd-wrapper in User Pinned).
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

function Remove-HermesStrayShortcutFiles {
    [CmdletBinding(SupportsShouldProcess)]
    param([Parameter(Mandatory)][string]$Dir)
    Get-ChildItem -LiteralPath $Dir -Filter '*.lnk' -File -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Name -match '^(test_|_test_)' -and $PSCmdlet.ShouldProcess($_.FullName, 'Remove', 'Stray test shortcut')) {
            Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
        }
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

$createPs1 = Join-Path $scriptDir 'create_taskbar_shortcuts.ps1'
if (-not (Test-Path -LiteralPath $createPs1)) {
    Write-Host ('[ERROR] ' + 'Ontbreekt: ' + $createPs1) -ForegroundColor Red
    exit 1
}

$icoGenPy = Join-Path $scriptDir (Join-Path 'tools' 'generate_colored_hermes_icons.py')
if (Test-Path -LiteralPath $icoGenPy) {
    if (-not $Quiet) {
        Write-Host '[INFO] Icoonset opnieuw genereren...' -ForegroundColor Gray
    }
    [void](Invoke-HermesColoredIconsFromPng -IconGeneratorPy $icoGenPy -Quiet)
}

Remove-HermesStrayShortcutFiles -Dir $scriptDir
Remove-HermesTaskbarShortcutFiles -Dir $scriptDir
& $createPs1 -RepoRoot $RepoRoot -OutDir $scriptDir -Quiet:$Quiet

$startBatFull = Join-Path $RepoRoot (Get-HermesStartLauncherRelativePath -RepoRoot $RepoRoot)
$pinRows = @(
    @{ Lnk = 'Hermes - update - naar taakbalk slepen.lnk'; Bat = 'UPDATE_HERMES.bat'; Role = 'Update' },
    @{ Lnk = 'Hermes - setup Windows - naar taakbalk slepen.lnk'; Bat = 'setup_hermes_windows.bat'; Role = 'Setup' },
    @{ Lnk = 'Start Hermes - naar taakbalk slepen.lnk'; Bat = ''; Role = 'Start' },
    @{ Lnk = 'Hermes - backup - naar taakbalk slepen.lnk'; Bat = 'MANAGE_BACKUPS.bat'; Role = 'Backup' }
    @{ Lnk = 'Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk'; Bat = 'RAG_KNOWLEDGE_UPDATE.bat'; Role = 'Rag' }
)

$pinnedDir = Join-Path $env:APPDATA (Join-Path 'Microsoft' (Join-Path 'Internet Explorer' (Join-Path 'Quick Launch' (Join-Path 'User Pinned' 'TaskBar'))))
if (Test-Path -LiteralPath $pinnedDir) {
    foreach ($row in $pinRows) {
        $srcLnk = Join-Path $scriptDir $row.Lnk
        if (-not (Test-Path -LiteralPath $srcLnk)) { continue }
        $batPath = if ($row.Bat) { Join-Path $scriptDir $row.Bat } else { $startBatFull }
        if (-not (Test-Path -LiteralPath $batPath)) { continue }
        $iconPath = Get-HermesTaskbarRoleIconPath -Role $row.Role -WindowsDir $scriptDir
        $destLnk = Join-Path $pinnedDir ([IO.Path]::GetFileName($srcLnk))
        $keepOpen = ($row.Role -eq 'Rag')
        if (Set-HermesTaskbarPinShortcut -ShortcutPath $destLnk -TargetBatPath $batPath `
                -IconIcoPath $iconPath -WorkingDirectory $RepoRoot -KeepCmdWindowOpen:$keepOpen) {
            if (-not $Quiet) {
                Write-Host "  [OK] Taakbalk-pin bijgewerkt: $($row.Lnk)" -ForegroundColor Green
            }
        }
    }
} elseif (-not $Quiet) {
    Write-Host '  [INFO] Geen map User Pinned/TaskBar - pin handmatig via rechtsklik op .lnk in windows\.' -ForegroundColor Gray
}

$openBat = Join-Path $scriptDir 'OPEN_SETUP.bat'
if (Test-Path -LiteralPath $openBat) {
    $openIcon = Get-HermesTaskbarRoleIconPath -Role 'OpenSetup' -WindowsDir $scriptDir
    Set-HermesShellShortcut -ShortcutPath (Join-Path $scriptDir 'Hermes - Open Setup - naar taakbalk slepen.lnk') `
        -TargetBatPath $openBat -IconIcoPath $openIcon -WorkingDirectory $RepoRoot `
        -Description 'Hermes - volledige setup-wizard (OPEN_SETUP)' | Out-Null
}

Clear-HermesShellIconCache

if (-not $Quiet) {
    Write-Host ''
    Write-Host 'windows\*.lnk = cmd /c + multi-size .ico. Taakbalk-pin = zelfde wrapper.' -ForegroundColor Cyan
    Write-Host 'Verkenner: F5 in windows\. Nieuwe pin: sleep .lnk uit windows\ (niet .bat).' -ForegroundColor Gray
}

exit 0
