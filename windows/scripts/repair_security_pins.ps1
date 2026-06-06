# Security pins + verwijder optionele llama-cpp/diskcache (CVE-2025-69872, geen PyPI-fix).
param(
    [string]$RepoRoot = "",
    [switch]$SkipLlamaUninstall
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\HermesPythonPolicy.ps1")

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$pythons = @(Get-HermesRagPython -RepoRoot $RepoRoot)
if ($pythons.Count -eq 0) {
    $py = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
    if ($py) { $pythons = @($py) }
}
if ($pythons.Count -eq 0) {
    Write-Host "[ERROR] Geen Python met pip (hermes-env)" -ForegroundColor Red
    exit 1
}

$pins = Join-Path $RepoRoot "overlay\requirements-security-pins.txt"
if (-not (Test-Path -LiteralPath $pins)) {
    Write-Host "[ERROR] Ontbreekt: $pins" -ForegroundColor Red
    exit 1
}

$exitCode = 0
foreach ($py in $pythons) {
    Write-Host ("[INFO] Security pins via: {0}" -f $py) -ForegroundColor Cyan
    & $py -m pip install -r $pins
    if ($LASTEXITCODE -ne 0) { $exitCode = 1; continue }

    $guard = Join-Path $RepoRoot "scripts\guard_forbidden_packages.py"
    if ((-not $SkipLlamaUninstall) -and (Test-Path -LiteralPath $guard)) {
        & $py $guard --fix
    }

    $constraints = Join-Path $RepoRoot "overlay\constraints-rag-stack.txt"
    if (Test-Path -LiteralPath $constraints) {
        & $py -m pip install "transformers>=5.0.0" -c $constraints --quiet 2>$null
    }

    & $py -m pip install "PyNaCl==1.6.2" "setuptools>=77.0,<82" --quiet 2>$null
}

if ($exitCode -eq 0) {
    Write-Host "[OK] Security pins toegepast" -ForegroundColor Green
}
exit $exitCode
