# Roept scripts/deduplicate_memories.py aan via canonieke conda hermes-env.
param(
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')
$py = Get-HermesCondaPython
if (-not $py) {
    Write-Host '[FAIL] Geen hermes-env python (REPAIR_PYTHON.bat)' -ForegroundColor Red
    exit 1
}

$script = Join-Path $RepoRoot 'scripts/deduplicate_memories.py'
if (-not (Test-Path -LiteralPath $script)) {
    Write-Host '[FAIL] scripts/deduplicate_memories.py ontbreekt' -ForegroundColor Red
    exit 1
}

Write-Host '--- deduplicate_memories (hermes-env) ---' -ForegroundColor Cyan
& $py $script
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
exit 0
