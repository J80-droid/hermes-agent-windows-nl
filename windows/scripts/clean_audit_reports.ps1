# Verwijder lokale gitignored audit-artefacten (rapporten, E2E-logs).
# Veilig: alleen bestanden die git check-ignore bevestigt.
param(
    [string]$RepoRoot = '',
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host '[FAIL] git niet op PATH — clean_audit_reports vereist git check-ignore.' -ForegroundColor Red
    exit 1
}

$patterns = @('*REPORT*.md', '*E2E_LOG*', 'RUN_AUDITS*.log')
$scanRoots = @(
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'audits'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/audits')
)

$script:CleanAuditRemoved = 0
$script:CleanAuditBytes = 0L

foreach ($root in $scanRoots) {
    if (-not (Test-Path -LiteralPath $root)) { continue }
    foreach ($pat in $patterns) {
        Get-ChildItem -LiteralPath $root -Filter $pat -File -Recurse -ErrorAction SilentlyContinue |
            ForEach-Object {
                $ign = git -C $RepoRoot check-ignore $_.FullName 2>$null
                if (-not $ign) { return }
                if ($WhatIf) {
                    Write-Host "[WHATIF] $($_.FullName)" -ForegroundColor Yellow
                } else {
                    $script:CleanAuditBytes += $_.Length
                    Remove-Item -LiteralPath $_.FullName -Force
                }
                $script:CleanAuditRemoved++
            }
    }
}

if ($WhatIf) {
    Write-Host "[WHATIF] Zou $($script:CleanAuditRemoved) gitignored audit-artefact(en) verwijderen." -ForegroundColor Cyan
} else {
    $mb = [math]::Round($script:CleanAuditBytes / 1MB, 2)
    Write-Host "[OK] $($script:CleanAuditRemoved) gitignored audit-artefact(en) verwijderd ($mb MB)." -ForegroundColor Green
}
