#requires -Version 5.1
# Vernieuwt Hermes-snelkoppelingen (windows\, %LOCALAPPDATA%\Hermes\shortcuts) en taakbalk/bureaublad-pins.
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$RepoRoot = '',
    [switch]$Quiet,
    [switch]$SkipIconGen
)

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

if (-not $Quiet) {
    Write-Host ''
    Write-Host 'Snelkoppelingen staan in windows\ en %LOCALAPPDATA%\Hermes\shortcuts\.' -ForegroundColor Cyan
    Write-Host 'Taakbalk-pins blijven na update werken (paden/iconen worden in-place bijgewerkt).' -ForegroundColor Gray
    Write-Host 'Eenmalige pop-up over een dode pin? Klik Ja — daarna hoef je niet opnieuw te slepen.' -ForegroundColor DarkGray
}

exit 0
