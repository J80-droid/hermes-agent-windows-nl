# Output canoniek Python-pad (stdout) voor .bat for /f — dot-source policy.
param(
    [string]$RepoRoot = '',
    [switch]$RequirePip
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$py = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip:$RequirePip
if (-not $py) {
    [Console]::Error.WriteLine('Resolve-HermesPythonExe: geen conda hermes-env gevonden')
    exit 1
}
Write-Output $py
exit 0
