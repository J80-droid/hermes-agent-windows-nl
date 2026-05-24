# Snelle syntax-check voor audit-PS1 (zelfde als CI/PSScriptAnalyzer; IDE-cache kan achterlopen).
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $repo

$files = @(
    'windows\audits\RUN_STATUS_BAR_COST_E2E.ps1',
    'windows\audits\RUN_PARETO_E2E.ps1',
    'windows\audits\RUN_TRUST_FORENSIC_E2E.ps1',
    'windows\audits\TrustForensicE2E.core.ps1',
    'windows\audits\RUN_MEMORY_ARCHITECTURE_E2E.ps1',
    'windows\audits\MemoryArchitectureE2E.core.ps1',
    'windows\scripts\MemoryAuditCommon.ps1',
    'windows\scripts\HermesMemoryMergeCommon.ps1',
    'windows\WindowsLocalAssetsManifest.ps1'
)

$failed = 0
foreach ($rel in $files) {
    $path = Join-Path $repo $rel
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
    $settings = Join-Path $repo 'windows\PSScriptAnalyzerSettings.psd1'
    foreach ($rel in $files) {
        $path = Join-Path $repo $rel
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
