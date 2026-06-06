# E2E: memory identity repair (pre-audit scrub, post-sync, protocol keten).
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$corePs1 = Join-Path $PSScriptRoot 'MemoryIdentityRepairE2E.core.ps1'
$unitPs1 = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/tests/MemoryAuditCommon.Unit.Tests.ps1'
$legacyUnit = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'tests/windows/test_memory_identity_repair.ps1'

$failures = 0

Write-Host '=== Memory Identity Repair E2E ===' -ForegroundColor Cyan

Write-Host '--- 1/4 core E2E ---' -ForegroundColor Cyan
& $corePs1 -RepoRoot $repoRoot
if ($LASTEXITCODE -ne 0) {
    Write-Host '[FAIL] MemoryIdentityRepairE2E.core.ps1' -ForegroundColor Red
    $failures++
} else {
    Write-Host '[OK] MemoryIdentityRepairE2E.core.ps1' -ForegroundColor Green
}

Write-Host '--- 2/4 unit tests (windows/tests) ---' -ForegroundColor Cyan
if (Test-Path -LiteralPath $unitPs1) {
    & $unitPs1
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[FAIL] MemoryAuditCommon.Unit.Tests.ps1' -ForegroundColor Red
        $failures++
    } else {
        Write-Host '[OK] MemoryAuditCommon.Unit.Tests.ps1' -ForegroundColor Green
    }
} else {
    Write-Host '[FAIL] MemoryAuditCommon.Unit.Tests.ps1 ontbreekt' -ForegroundColor Red
    $failures++
}

Write-Host '--- 3/4 legacy unit runner ---' -ForegroundColor Cyan
& $legacyUnit
if ($LASTEXITCODE -ne 0) {
    Write-Host '[FAIL] test_memory_identity_repair.ps1' -ForegroundColor Red
    $failures++
} else {
    Write-Host '[OK] test_memory_identity_repair.ps1' -ForegroundColor Green
}

Write-Host '--- 4/4 pytest scrub_identity ---' -ForegroundColor Cyan
$python = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
if (Test-Path -LiteralPath $python) {
    $env:PYTHONPATH = $repoRoot
    Invoke-HermesAuditPytest -Python $python (Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'tests/windows/test_scrub_identity.py') -q --tb=no
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[FAIL] test_scrub_identity.py' -ForegroundColor Red
        $failures++
    } else {
        Write-Host '[OK] test_scrub_identity.py' -ForegroundColor Green
    }
} else {
    Write-Host '[WARN] pytest overgeslagen (geen hermes-env python)' -ForegroundColor Yellow
}

if ($failures -gt 0) {
    Write-Host ''
    Write-Host ('=== Memory Identity Repair E2E FAIL (' + $failures + ' blok(ken)) ===') -ForegroundColor Red
    exit 1
}
Write-Host ''
Write-Host '=== Memory Identity Repair E2E PASS ===' -ForegroundColor Green
exit 0
