# Snelle syntax-check voor audit-PS1 (zelfde als CI/PSScriptAnalyzer; IDE-cache kan achterlopen).
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $repo

$files = @(
    'windows/audits/RUN_STATUS_BAR_COST_E2E.ps1',
    'windows/audits/RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1',
    'windows/audits/ClassicCliStatusBarCostE2E.core.ps1',
    'windows/audits/RUN_PARETO_E2E.ps1',
    'windows/audits/RUN_PSEUDO_TABLE_NORMALIZER_E2E.ps1',
    'windows/audits/PseudoTableNormalizerE2E.core.ps1',
    'windows/audits/RUN_CODEBASE_SMOKE_AUDIT.ps1',
    'windows/audits/RUN_CODEBASE_SMOKE_E2E.ps1',
    'windows/audits/RUN_TRUST_FORENSIC_E2E.ps1',
    'windows/audits/TrustForensicE2E.core.ps1',
    'windows/audits/RUN_MEMORY_ARCHITECTURE_E2E.ps1',
    'windows/audits/MemoryArchitectureE2E.core.ps1',
    'windows/scripts/MemoryAuditCommon.ps1',
    'windows/scripts/HermesMemoryMergeCommon.ps1',
    'windows/WindowsLocalAssetsManifest.ps1',
    'windows/upstream_sync.ps1',
    'windows/scripts/Invoke-UpstreamPostMerge.ps1',
    'windows/scripts/Invoke-PostSyncCodebaseSmoke.ps1',
    'windows/scripts/Invoke-TrustRuntimeLight.ps1',
    'windows/scripts/launch_pending_trust_runtime.ps1',
    'windows/audits/PendingTrustStartE2E.core.ps1',
    'windows/audits/RUN_PENDING_TRUST_START_E2E.ps1',
    'windows/audits/WindowsPlatformHardeningE2E.core.ps1',
    'windows/audits/RUN_PLATFORM_HARDENING_PRODUCTION_GATE.ps1',
    'windows/audits/HermesPythonInstitutionalE2E.core.ps1',
    'windows/audits/HermesPythonInstitutionalE2E.harness.ps1',
    'windows/audits/RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.ps1',
    'windows/audits/RUN_INSTITUTIONAL_PRODUCTION_GATE.ps1',
    'windows/scripts/resolve_hermes_python.ps1',
    'windows/scripts/validate_windows_python_wiring.ps1',
    'windows/scripts/check_hermes_rag_after_repair.ps1',
    'windows/audits/HermesPythonInstitutionalRegressionE2E.core.ps1',
    'windows/audits/HermesPythonInstitutionalRegressionE2E.harness.ps1',
    'windows/audits/RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E.ps1'
)

$failed = 0
foreach ($rel in $files) {
    $path = Join-HermesRepoPath -RepoRoot $repo -RelativePath $rel
    $parseErr = [System.Collections.Generic.List[object]]::new()
    $null = [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$parseErr)
    if ($parseErr.Count -gt 0) {
        Write-Host "[FAIL] $rel" -ForegroundColor Red
        $parseErr | ForEach-Object { Write-Host "  $($_.Message)" }
        $failed++
    } else {
        Write-Host "[OK] $rel" -ForegroundColor Green
    }
}

if (Get-Module -ListAvailable PSScriptAnalyzer) {
    Import-Module PSScriptAnalyzer -Force
    $settings = Join-HermesRepoPath -RepoRoot $repo -RelativePath 'windows/PSScriptAnalyzerSettings.psd1'
    foreach ($rel in $files) {
        $path = Join-HermesRepoPath -RepoRoot $repo -RelativePath $rel
        $issues = Invoke-ScriptAnalyzer -Path $path -Settings $settings -Severity Error
        if ($issues) {
            Write-Host "[PSSA] $rel" -ForegroundColor Red
            $issues | ForEach-Object { Write-Host "  L$($_.Line): $($_.Message)" }
            $failed++
        }
    }
}

if ($failed -gt 0) { exit 1 }
Write-Host 'Alle audit-PS1 bestanden: syntax OK' -ForegroundColor Green
exit 0
