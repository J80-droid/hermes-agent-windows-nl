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

function Remove-HermesDuplicatePinnedTaskbarShortcuts {
    <#
    .SYNOPSIS
        Verwijdert Windows-duplicaten zoals "Hermes - update - (2).lnk" in User Pinned\TaskBar.
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param([Parameter(Mandatory)][string]$Dir)
    if (-not (Test-Path -LiteralPath $Dir)) { return }
    Get-ChildItem -LiteralPath $Dir -Filter 'Hermes*.lnk' -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match ' \(\d+\)\.lnk$' } |
        ForEach-Object {
            if ($PSCmdlet.ShouldProcess($_.FullName, 'Remove', 'Duplicate Hermes taskbar pin')) {
                Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
                if (-not $Quiet) {
                    Write-Host "  [INFO] Dubbele pin verwijderd: $($_.Name)" -ForegroundColor DarkGray
                }
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
        'Hermes - Open Setup - naar taakbalk slepen.lnk',
        'Hermes - Obsidian vault - naar taakbalk slepen.lnk'
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

$pinRows = @(
    @{ Lnk = 'Hermes - update - naar taakbalk slepen.lnk'; Role = 'Update' },
    @{ Lnk = 'Hermes - setup Windows - naar taakbalk slepen.lnk'; Role = 'Setup' },
    @{ Lnk = 'Hermes - backup - naar taakbalk slepen.lnk'; Role = 'Backup' },
    @{ Lnk = 'Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk'; Role = 'Restore' },
    @{ Lnk = 'Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk'; Role = 'Rag' },
    @{ Lnk = 'Hermes - Obsidian vault - naar taakbalk slepen.lnk'; Role = 'Obsidian' },
    @{ Lnk = 'Start Hermes - naar taakbalk slepen.lnk'; Role = 'Start' },
    @{ Lnk = 'Start Hermes (snel) - naar taakbalk slepen.lnk'; Role = 'StartFast' }
)

$pinnedDir = Join-Path $env:APPDATA (Join-Path 'Microsoft' (Join-Path 'Internet Explorer' (Join-Path 'Quick Launch' (Join-Path 'User Pinned' 'TaskBar'))))
if (Test-Path -LiteralPath $pinnedDir) {
    Remove-HermesDuplicatePinnedTaskbarShortcuts -Dir $pinnedDir
    foreach ($row in $pinRows) {
        $srcLnk = Join-Path $scriptDir $row.Lnk
        if (-not (Test-Path -LiteralPath $srcLnk)) { continue }
        $batPath = Get-HermesShortcutResolvedBatPath -ShortcutPath $srcLnk
        if (-not $batPath) {
            if ($row.Role -eq 'Start') {
                $batPath = Join-Path $RepoRoot (Get-HermesStartLauncherRelativePath -RepoRoot $RepoRoot -LaunchProfile full)
            } elseif ($row.Role -eq 'StartFast') {
                $batPath = Join-Path $RepoRoot (Get-HermesStartLauncherRelativePath -RepoRoot $RepoRoot -LaunchProfile minimal)
            }
        }
        if (-not $batPath -or -not (Test-Path -LiteralPath $batPath)) { continue }
        $iconPath = Get-HermesTaskbarRoleIconPath -Role $row.Role -WindowsDir $scriptDir
        $destLnk = Join-Path $pinnedDir ([IO.Path]::GetFileName($srcLnk))
        $keepOpen = ($row.Role -eq 'Rag')
        $pinOk = if ($row.Role -eq 'Start') {
            Set-HermesStartShellShortcut -ShortcutPath $destLnk -RepoRoot $RepoRoot -IconIcoPath $iconPath -LaunchProfile full
        } elseif ($row.Role -eq 'StartFast') {
            Set-HermesStartShellShortcut -ShortcutPath $destLnk -RepoRoot $RepoRoot -IconIcoPath $iconPath -LaunchProfile minimal
        } else {
            Set-HermesTaskbarPinShortcut -ShortcutPath $destLnk -TargetBatPath $batPath `
                -IconIcoPath $iconPath -WorkingDirectory $RepoRoot -KeepCmdWindowOpen:$keepOpen
        }
        if ($pinOk) {
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

$obsidianBat = Join-Path $scriptDir 'OPEN_OBSIDIAN_VAULT.bat'
if (Test-Path -LiteralPath $obsidianBat) {
    $obsIcon = Get-HermesTaskbarRoleIconPath -Role 'Obsidian' -WindowsDir $scriptDir
    Set-HermesShellShortcut -ShortcutPath (Join-Path $scriptDir 'Hermes - Obsidian vault - naar taakbalk slepen.lnk') `
        -TargetBatPath $obsidianBat -IconIcoPath $obsIcon -WorkingDirectory $RepoRoot `
        -Description 'Hermes Knowledge (Obsidian L4-vault)' | Out-Null
}

Clear-HermesShellIconCache

if (-not $Quiet) {
    Write-Host ''
    Write-Host 'windows\*.lnk = wt.exe + cmd /c call (zelfde als Start). Taakbalk-pin = kopie.' -ForegroundColor Cyan
    Write-Host 'Verkenner: F5 in windows\. Nieuwe pin: sleep .lnk uit windows\ (niet .bat).' -ForegroundColor Gray
}

exit 0
