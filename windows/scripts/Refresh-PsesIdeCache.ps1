# Vernieuwt PSES/IDE-analyse: touch fork-kritieke scripts + AST-check.
# Onderdeel van Apply-HermesWorkspaceIdeSettings.ps1; ook los:
#   powershell -File windows\scripts\Refresh-PsesIdeCache.ps1
# Parent workspace: windows\APPLY_WORKSPACE_IDE_SETTINGS.bat — zie docs\WORKSPACE_IDE_SETUP.md
# Daarna in Cursor: PowerShell: Restart Session + Developer: Reload Window.
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$targets = @(
    'windows\HermesShellCommon.ps1',
    'windows\scripts\Invoke-MemoryTrustPostSync.ps1',
    'windows\scripts\MemoryAuditCommon.ps1',
    'windows\scripts\TrustRuntimePending.psm1',
    'windows\audits\MemoryIdentityRepairE2E.core.ps1',
    'windows\audits\PendingTrustStartE2E.core.ps1',
    'windows\audits\RUN_SOUL_DEPLOY_START_E2E.ps1'
)
$now = Get-Date
$failed = 0
foreach ($rel in $targets) {
    $path = Join-Path $repoRoot $rel
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host ('MISSING: ' + $rel)
        $failed++
        continue
    }
    (Get-Item -LiteralPath $path).LastWriteTime = $now
    $parseErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$parseErrors)
    if ($parseErrors -and $parseErrors.Count -gt 0) {
        Write-Host ('AST FAIL: ' + $rel)
        foreach ($e in $parseErrors) {
            Write-Host ('  L' + $e.Extent.StartLineNumber + ':' + $e.Extent.StartColumnNumber + ' ' + $e.Message)
        }
        $failed++
    } else {
        Write-Host ('OK: ' + $rel)
    }
}
if ($failed -gt 0) { exit 1 }
Write-Host 'PSES cache refresh: bestanden getouched, AST groen. Herstart PowerShell-sessie in IDE.'
exit 0
