# Snelle AST-check voor bekende Hermes windows-scripts (PSES/PSSA sanity).
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$files = @(
    'windows/audits/RUN_TOOLSET_DOMAIN_E2E.ps1',
    'windows/scripts/SyncSoulSnippet.psm1',
    'windows/audits/RUN_MEMORY_ARCHITECTURE_E2E.ps1',
    'windows/scripts/HermesBackupCommon.ps1',
    'windows/scripts/log_trust_memory_user_snapshot.ps1'
)
$fail = 0
foreach ($rel in $files) {
    $path = Join-Path $repoRoot $rel
    $errs = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$errs)
    if ($errs) {
        Write-Host "[FAIL] $rel" -ForegroundColor Red
        foreach ($e in $errs) {
            Write-Host ("  L{0}: {1}" -f $e.Extent.StartLineNumber, $e.Message) -ForegroundColor DarkRed
        }
        $fail++
    } else {
        Write-Host "[OK]   $rel" -ForegroundColor Green
    }
}
if ($fail -gt 0) { exit 1 }
Write-Host 'Alle parse-checks OK.' -ForegroundColor Cyan
exit 0
