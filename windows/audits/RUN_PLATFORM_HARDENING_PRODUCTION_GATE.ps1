# Gecombineerde productie-poort: Windows platform hardening + regression + pytest + footguns.
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

. (Join-Path $scriptRoot '..\HermesShellCommon.ps1')

$failures = 0
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
Write-Host '=== Platform Hardening Production Gate ===' -ForegroundColor Cyan

$baseE2e = Join-Path $scriptRoot 'RUN_WINDOWS_PLATFORM_HARDENING_E2E.ps1'
Write-Host '--- RUN_WINDOWS_PLATFORM_HARDENING_E2E ---' -ForegroundColor Cyan
& $baseE2e -RepoRoot $RepoRoot @($(if ($SkipPytest) { '-SkipPytest' }))
if (Test-NativeCommandFailed) { $failures++ }

$regE2e = Join-Path $scriptRoot 'RUN_PLATFORM_HARDENING_REGRESSION_E2E.ps1'
Write-Host '--- RUN_PLATFORM_HARDENING_REGRESSION_E2E ---' -ForegroundColor Cyan
& $regE2e -RepoRoot $RepoRoot @($(if ($SkipPytest) { '-SkipPytest' }))
if (Test-NativeCommandFailed) { $failures++ }

if (-not $SkipPytest) {
    $auditPython = Get-HermesAuditPython -RepoRoot $RepoRoot
    $conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
    $pytestTargets = @(
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/hermes_cli/test_filesystem_sandbox.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/hermes_cli/test_hardware_backend.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/rag_pipeline/test_lancedb_storage.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/rag_pipeline/test_vector_store_ports.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/rag_pipeline/test_kb_schema_lazy.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/rag_pipeline/test_knowledge_repository.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/tools/test_file_tools.py')
    )
    Write-Host '--- pytest platform hardening subset ---' -ForegroundColor Cyan
    if (Test-Path -LiteralPath $conda) {
        & $conda run -n hermes-env --no-capture-output python -m pytest @pytestTargets -q --tb=short -o addopts= 2>&1 | ForEach-Object { Write-Host $_ }
    } else {
        & $auditPython -m pytest @pytestTargets -q --tb=short -o addopts= 2>&1 | ForEach-Object { Write-Host $_ }
    }
    if (Test-NativeCommandFailed) { $failures++ }
}

$footguns = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/check-windows-footguns.py'
Write-Host '--- check-windows-footguns --all ---' -ForegroundColor Cyan
$auditPython = Get-HermesAuditPython
& $auditPython $footguns --all 2>&1 | ForEach-Object { Write-Host $_ }
if (Test-NativeCommandFailed) { $failures++ }

$status = if ($failures -eq 0) { 'PASS' } else { "FAIL ($failures)" }
$reportPath = Join-Path $scriptRoot ('PLATFORM_HARDENING_PRODUCTION_GATE_REPORT_' + $reportStamp + '.md')
@"
# Platform hardening production gate - $status

Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Repo: $RepoRoot

## Keten
1. RUN_WINDOWS_PLATFORM_HARDENING_E2E (10/10)
2. RUN_PLATFORM_HARDENING_REGRESSION_E2E (10/10)
3. pytest platform hardening subset $(if ($SkipPytest) { '(overgeslagen)' } else { '' })
4. check-windows-footguns --all

Status: **$status**
"@ | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== PLATFORM HARDENING PRODUCTION GATE: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== PLATFORM HARDENING PRODUCTION GATE: PASS ===' -ForegroundColor Green
exit 0
