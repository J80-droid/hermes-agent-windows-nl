# Repareer Codebase Viz pygount-schijfcache (verwijdert ongeldige cache, bouwt opnieuw op).
# Aangeroepen vanuit windows\FIX_CODEBASE_VIZ_CACHE.bat
param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$winDir = Split-Path -Parent $PSScriptRoot
. (Join-Path $winDir 'HermesShellCommon.ps1')

if (-not $RepoRoot) {
    if ($env:HERMES_REPO_ROOT) { $RepoRoot = $env:HERMES_REPO_ROOT }
    else { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}
$env:HERMES_REPO_ROOT = $RepoRoot

$code = Repair-HermesCodebaseVizPygountCache -RepoRoot $RepoRoot -Quiet:$Quiet
exit $code
