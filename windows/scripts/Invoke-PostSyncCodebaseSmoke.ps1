# Optionele codebase smoke na POST_GIT_PULL / upstream post-merge (geen E3).
param(
    [Parameter(Mandatory)]
    [string]$RepoRoot,
    [ValidateSet('Smoke', 'E2E')]
    [string]$Level = 'E2E'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

$audits = Join-Path $PSScriptRoot '..\audits'
if ($Level -eq 'E2E') {
    $script = Join-Path $audits 'RUN_CODEBASE_SMOKE_E2E.ps1'
    $label = 'Codebase smoke E2E (E1/E2, geen E3)'
} else {
    $script = Join-Path $audits 'RUN_CODEBASE_SMOKE_AUDIT.ps1'
    $label = 'Codebase smoke audit (E1/E2, geen E3/E2E-guardrails)'
}

if (-not (Test-Path -LiteralPath $script)) {
    Write-Host "[ERROR] Ontbreekt: $script" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] $label..." -ForegroundColor Cyan
& $script -RepoRoot $RepoRoot
if ($LASTEXITCODE -ne 0) {
    if ($Level -eq 'E2E') {
        Write-Host '[ERROR] Zie CODEBASE_SMOKE_E2E_REPORT_*.md in windows/audits/' -ForegroundColor Red
    } else {
        Write-Host '[ERROR] Zie CODEBASE_SMOKE_AUDIT_REPORT_*.md in windows/audits/' -ForegroundColor Red
    }
    exit $LASTEXITCODE
}
Write-Host "[OK] $label geslaagd." -ForegroundColor Green
exit 0
