#requires -Version 5.1
# Institutioneel: conda hermes-env afdwingen; kapotte repo\.venv in quarantaine.
param(
    [string]$RepoRoot = '',
    [switch]$Quiet,
    [switch]$SkipQuarantine
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
    Write-Host $Text -ForegroundColor $Color
}

if (-not $SkipQuarantine) {
    [void](Invoke-HermesQuarantineBrokenVenv -RepoRoot $RepoRoot -Quiet:$Quiet)
}

$py = Get-HermesPreferredPython -RepoRoot $RepoRoot
if (-not $py) {
    Write-PolicyMsg '[ERROR] Geen conda hermes-env gevonden. Maak env aan of zet HERMES_PYTHON.' 'Red'
    Write-PolicyMsg '  conda create -n hermes-env python=3.12 -y' 'Yellow'
    exit 1
}

if (-not (Test-HermesPythonHasPip -PythonExe $py)) {
    Write-PolicyMsg "[ERROR] Geen pip in $py" 'Red'
    exit 1
}

$policyDir = Join-Path $env:LOCALAPPDATA 'Hermes'
New-Item -ItemType Directory -Force -Path $policyDir | Out-Null
@{
    preferred_python = $py
    conda_env        = (Get-HermesCondaEnvName)
    updated_utc      = (Get-Date).ToUniversalTime().ToString('o')
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $policyDir 'python-policy.json') -Encoding UTF8

Write-PolicyMsg "[OK] Canonieke Python: $py" 'Green'
if (Test-Path -LiteralPath (Join-Path $RepoRoot '.venv')) {
    Write-PolicyMsg '[WARN] .venv bestaat nog — draai REPAIR_PYTHON.bat of verwijder handmatig.' 'Yellow'
}
exit 0
