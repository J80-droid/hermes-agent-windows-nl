# Verwijder UTF-8 BOM uit root + profiel auth.json (fork overlay).
param(
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\HermesPythonPolicy.ps1")

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$py = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
if (-not $py) {
    Write-Host "[ERROR] Geen Python (hermes-env)" -ForegroundColor Red
    exit 1
}

$script = Join-Path $RepoRoot "scripts\repair_auth_json_bom.py"
Push-Location $RepoRoot
try {
    & $py $script
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
