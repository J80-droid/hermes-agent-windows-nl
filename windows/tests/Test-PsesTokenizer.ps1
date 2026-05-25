# Valideert PowerShell AST-parse (zelfde tokenizer als PSES) voor fork-kritieke scripts.
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$targets = @(
    'windows/apply_hermes_home_migration.ps1',
    'windows/HermesPythonPolicy.ps1',
    'windows/HermesShellCommon.ps1',
    'windows/upstream_sync.ps1',
    'windows/sync_hermes_api_env.ps1',
    'windows/scripts/audit_profile_memories.ps1',
    'windows/scripts/MemoryAuditCommon.ps1',
    'windows/scripts/repair_runtime_identity.ps1',
    'windows/scripts/Invoke-MemoryTrustPostSync.ps1',
    'windows/scripts/scrub_identity_to_J.ps1',
    'windows/tests/MemoryAuditCommon.Unit.Tests.ps1',
    'windows/audits/MemoryIdentityRepairE2E.core.ps1',
    'windows/audits/RUN_MEMORY_IDENTITY_REPAIR_E2E.ps1',
    'windows/scripts/check_hermes_rag_after_repair.ps1',
    'windows/scripts/HermesHomeCommon.ps1',
    'windows/scripts/HermesMemoryMergeCommon.ps1',
    'windows/scripts/TrustRuntimePending.psm1',
    'windows/audits/UpstreamMergeIntegrationE2E.core.ps1',
    'windows/audits/UpstreamSyncPhase2E2E.core.ps1'
)
$failed = 0
foreach ($rel in $targets) {
    $path = Join-Path $repoRoot $rel
    $parseErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$parseErrors)
    if ($parseErrors -and $parseErrors.Count -gt 0) {
        Write-Host ('FAIL: ' + $rel) -ForegroundColor Red
        foreach ($e in $parseErrors) {
            Write-Host ("  L{0}:{1} {2}" -f $e.Extent.StartLineNumber, $e.Extent.StartColumnNumber, $e.Message)
        }
        $failed++
    } else {
        Write-Host ('OK: ' + $rel) -ForegroundColor Green
    }
}
if ($failed -gt 0) { exit 1 }
exit 0
