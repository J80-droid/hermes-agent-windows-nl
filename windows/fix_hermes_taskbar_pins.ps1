#requires -Version 5.1
# Vernieuwt Hermes-snelkoppelingen (windows\, %LOCALAPPDATA%\Hermes\shortcuts) en taakbalk/bureaublad-pins.
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$RepoRoot = '',
    [switch]$Quiet,
    [switch]$SkipIconGen,
    [switch]$PostUpdateGuidance
)

function Write-HermesTaskbarPostUpdateGuidance {
    Write-Host ''
    Write-Host '[INFO] Taakbalk — als een pin nog "item kan niet worden geopend" geeft:' -ForegroundColor Cyan
    Write-Host '       1) Klik die taakbalk-pin -> Ja (alleen de dode pin)' -ForegroundColor Gray
    Write-Host '       2) Rechtsklik windows\Start Hermes - naar taakbalk slepen.lnk (of andere rol)' -ForegroundColor Gray
    Write-Host '          -> Vastmaken aan taakbalk (niet slepen)' -ForegroundColor Gray
    Write-Host '       Verkenner-snelkoppelingen in windows\ blijven gewoon werken.' -ForegroundColor DarkGray
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
    Write-HermesTaskbarPostUpdateGuidance
} elseif (-not $Quiet) {
    Write-Host ''
    Write-Host 'Snelkoppelingen: windows\ (dubbelklik, wt.exe) + taakbalk-map (bat-doel).' -ForegroundColor Cyan
    Write-HermesTaskbarPostUpdateGuidance
}

exit 0
