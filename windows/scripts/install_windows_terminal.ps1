#requires -Version 5.1
<#
.SYNOPSIS
    Installeert Windows Terminal (wt.exe) via winget indien nodig.
.DESCRIPTION
    Idempotent. Controleert PATH, WindowsApps-alias en winget-lijst.
    Zie windows/requirements-windows.txt en WINDOWS_REQUIREMENTS.md.
#>
[CmdletBinding()]
param(
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$wingetId = 'Microsoft.WindowsTerminal'

function Write-InstallLog {
    param([string]$Message, [string]$Level = 'INFO')
    if ($Quiet) { return }
    $color = switch ($Level) {
        'OK' { 'Green' }
        'WARN' { 'Yellow' }
        'ERROR' { 'Red' }
        default { 'Cyan' }
    }
    Write-Host "[$Level] $Message" -ForegroundColor $color
}

function Test-HermesWindowsTerminalAvailable {
    if (Get-Command wt.exe -ErrorAction SilentlyContinue) { return $true }
    if (Get-Command wt -ErrorAction SilentlyContinue) { return $true }
    $alias = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\wt.exe'
    if (Test-Path -LiteralPath $alias) { return $true }
    return $false
}

function Get-HermesWindowsTerminalWingetInstalled {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { return $false }
    try {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = 'SilentlyContinue'
        $out = winget list --id $wingetId --accept-source-agreements 2>&1
        $ErrorActionPreference = $prev
        return ($out -match $wingetId)
    } catch {
        return $false
    }
}

if (Test-HermesWindowsTerminalAvailable) {
    Write-InstallLog 'Windows Terminal (wt.exe) is al beschikbaar.' 'OK'
    exit 0
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-InstallLog 'winget ontbreekt. Installeer Windows Terminal via Microsoft Store of App Installer.' 'ERROR'
    Write-InstallLog 'https://aka.ms/terminal' 'WARN'
    exit 1
}

if (Get-HermesWindowsTerminalWingetInstalled) {
    Write-InstallLog 'Windows Terminal staat in winget, maar wt.exe is nog niet op PATH.' 'WARN'
    Write-InstallLog 'Open een nieuw venster of log opnieuw in; controleer App execution aliases voor wt.' 'WARN'
    exit 0
}

Write-InstallLog "Installeren: winget install $wingetId ..."
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    winget install $wingetId `
        --accept-package-agreements `
        --accept-source-agreements `
        --disable-interactivity 2>&1 | ForEach-Object {
            if (-not $Quiet) { Write-Host $_ }
        }
} finally {
    $ErrorActionPreference = $prevEap
}

$env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')

if (Test-HermesWindowsTerminalAvailable) {
    Write-InstallLog 'Windows Terminal geïnstalleerd.' 'OK'
    exit 0
}

Write-InstallLog 'Installatie voltooid; wt.exe nog niet zichtbaar in deze sessie.' 'WARN'
Write-InstallLog 'Start een nieuw Windows Terminal-venster en probeer: wt -h' 'WARN'
exit 0
