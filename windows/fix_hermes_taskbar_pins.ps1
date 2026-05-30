#requires -Version 5.1
# Vernieuwt Hermes-snelkoppelingen (windows\, %LOCALAPPDATA%\Hermes\shortcuts) en taakbalk/bureaublad-pins.
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$RepoRoot = '',
    [switch]$Quiet,
    [switch]$SkipIconGen,
    [switch]$PostUpdateGuidance,
    [switch]$OpenStableFolder
)

function Write-HermesTaskbarPostUpdateGuidance {
    param([switch]$OpenStableFolder)
    $stable = Get-HermesStableTaskbarShortcutsDir
    Write-Host ''
    Write-Host '[INFO] Taakbalk: NIET opnieuw slepen uit windows\ of backups\ na elke update.' -ForegroundColor Cyan
    Write-Host '       Eénmalig: rechtsklik Vastmaken aan taakbalk op bestanden in:' -ForegroundColor Gray
    if ($stable) {
        Write-Host ('          ' + $stable) -ForegroundColor White
        Write-Host '       (Hermes Start.lnk, Hermes Update.lnk, … — vaste paden buiten git)' -ForegroundColor DarkGray
    } else {
        Write-Host '          %LOCALAPPDATA%\Hermes\taakbalk\' -ForegroundColor Gray
    }
    Write-Host '       Na UPDATE_HERMES: bestaande pins worden automatisch bijgewerkt (zelfde .lnk op de balk).' -ForegroundColor DarkGray
    Write-Host '       windows\ *-naar-taakbalk-slepen.lnk = alleen Verkenner/dubbelklik.' -ForegroundColor DarkGray
    Write-Host '       Kapotte pin-pop-up? Klik Ja, daarna éénmalig opnieuw vastmaken vanuit taakbalk-map hierboven.' -ForegroundColor DarkGray
    if ($OpenStableFolder -and $stable -and (Test-Path -LiteralPath $stable)) {
        Start-Process -FilePath 'explorer.exe' -ArgumentList $stable
    }
}

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $RepoRoot.Trim()) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptDir '..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}

. (Join-Path $scriptDir 'HermesIconGeneratorInvoke.ps1')
. (Join-Path $scriptDir 'scripts\HermesPersistentShortcuts.ps1')

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

$legacy = @(
    'Hermes Agent - naar taakbalk slepen.lnk'
)
foreach ($leaf in $legacy) {
    $p = Join-Path $scriptDir $leaf
    if (Test-Path -LiteralPath $p) {
        Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
    }
}

Remove-HermesStrayShortcutFiles -Dir $scriptDir

[void](Invoke-HermesShortcutSyncRepair -RepoRoot $RepoRoot -WindowsDir $scriptDir -Quiet:$Quiet -SkipIconGen:$SkipIconGen)
Clear-HermesShellIconCache

if ($PostUpdateGuidance) {
    Write-HermesTaskbarPostUpdateGuidance -OpenStableFolder:$OpenStableFolder
} elseif (-not $Quiet) {
    Write-Host ''
    Write-Host 'Snelkoppelingen: windows\ (dubbelklik, wt.exe) + taakbalk-map (bat-doel).' -ForegroundColor Cyan
    Write-HermesTaskbarPostUpdateGuidance
}

exit 0
