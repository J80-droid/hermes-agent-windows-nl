# Lightweight backup schema v3 E2E (HermesBackupCommon + persona-subset).
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$testPs1 = Join-Path $repoRoot 'tests/windows/test_backup_runtime.ps1'
if (-not (Test-Path -LiteralPath $testPs1)) {
    Write-Host '[FAIL] tests/windows/test_backup_runtime.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}
& $testPs1
exit $LASTEXITCODE
