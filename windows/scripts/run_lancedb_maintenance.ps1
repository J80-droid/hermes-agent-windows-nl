# LanceDB onderhoud (list / inspect / compact / benchmark) via conda hermes-env.
param(
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'
$scriptDir = $PSScriptRoot
if (-not $RepoRoot -or $RepoRoot.StartsWith('-')) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
}
Set-Location -LiteralPath $RepoRoot

. (Join-Path (Join-Path $RepoRoot 'windows') 'HermesPythonPolicy.ps1')
$py = Get-HermesPreferredPython -RepoRoot $RepoRoot
if (-not $py) {
    Write-Host '[ERROR] hermes-env python niet gevonden. Zie REPAIR_PYTHON.bat' -ForegroundColor Red
    exit 1
}

$cli = Join-Path $RepoRoot 'scripts\rag_pipeline\lancedb_maintenance.py'
& $py $cli @args
exit $LASTEXITCODE
