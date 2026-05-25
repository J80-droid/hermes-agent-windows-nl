# Dunne launcher: sync IDE interpreter naar conda hermes-env.
param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$result = Update-HermesVscodeInterpreterPath -RepoRoot $RepoRoot -Quiet:$Quiet
if (-not $result.Ok) {
    if (-not $Quiet) {
        Write-Host ('[WARN] ' + $result.Message) -ForegroundColor Yellow
    }
    exit 1
}
exit 0
