#requires -Version 5.1
# Institutioneel: conda hermes-env afdwingen; kapotte repo\.venv in quarantaine.
param(
    [string]$RepoRoot = '',
    [switch]$Quiet,
    [switch]$SkipQuarantine,
    [switch]$SyncIde
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

function Write-PolicyMsg([string]$Text, [string]$Color = 'Gray') {
    if ($Quiet) { return }
    if ($global:HermesLaunchVisualState -and $global:HermesLaunchVisualState.SpinnerActive) {
        Add-HermesLaunchLogLine -Message $Text
        return
    }
    if ((Get-Command Test-HermesLaunchConsoleCapture -ErrorAction SilentlyContinue) -and (Test-HermesLaunchConsoleCapture)) {
        Add-HermesLaunchLogLine -Message $Text
        return
    }
    Write-Host $Text -ForegroundColor $Color
}

if (-not $SkipQuarantine) {
    [void](Invoke-HermesQuarantineBrokenVenv -RepoRoot $RepoRoot -Quiet:$Quiet)
}

$py = Get-HermesPreferredPython -RepoRoot $RepoRoot
[void](Repair-HermesPipTildeSitePackages -PythonExe $py -Quiet:$Quiet)
if (-not $py) {
    Write-PolicyMsg '[ERROR] Geen conda hermes-env gevonden. Maak env aan of zet HERMES_PYTHON.' 'Red'
    Write-PolicyMsg '  conda create -n hermes-env python=3.12 -y' 'Yellow'
    exit 1
}

if (-not (Test-HermesPythonHasPip -PythonExe $py)) {
    Write-PolicyMsg "[ERROR] Geen pip in $py" 'Red'
    exit 1
}

Write-HermesPythonPolicyManifest -PythonExe $py | Out-Null
Write-PolicyMsg "[OK] Canonieke Python: $py" 'Green'

if (Test-HermesRepoDotVenvPresent -RepoRoot $RepoRoot) {
    Write-PolicyMsg '[WARN] repo\.venv bestaat nog — niet canoniek. Draai REPAIR_PYTHON.bat (Hermes/Cursor sluiten) of verwijder handmatig.' 'Yellow'
    Write-PolicyMsg '  Productie-default: alleen conda hermes-env. Geen HERMES_ALLOW_UV_VENV tenzij bewust uv/venv naast conda.' 'DarkYellow'
}

if ($SyncIde) {
    [void](Invoke-HermesSyncIdePython -RepoRoot $RepoRoot -Quiet:$Quiet)
}

exit 0
