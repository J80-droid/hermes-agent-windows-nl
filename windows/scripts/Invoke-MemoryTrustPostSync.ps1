# Na SYNC_TRUST_RUNTIME: audit, productie-poort, /new-reminder (volledig geautomatiseerd).
param(
    [string]$RepoRoot = '',
    [string]$HermesRuntimeRoot = '',
    [switch]$SkipProductionGate,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'MemoryAuditCommon.ps1')
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

if ($env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB -notin @('1', 'true', 'True', 'yes', 'Yes')) {
    if (-not $Quiet) {
        Write-Host '--- Repair-HermesRuntimeIdentity (pre-audit) ---' -ForegroundColor Cyan
    }
    $scrubParams = @{ Quiet = $Quiet }
    if ($HermesRuntimeRoot) { $scrubParams['HermesRoot'] = $HermesRuntimeRoot }
    $scrubResult = Repair-HermesRuntimeIdentity @scrubParams
    if (-not $Quiet -and $scrubResult.FilesChanged -eq 0) {
        Write-Host '[INFO] Runtime identity: geen wijzigingen nodig' -ForegroundColor DarkGray
    }
} elseif (-not $Quiet) {
    Write-Host '[INFO] Runtime identity scrub overgeslagen (HERMES_SKIP_RUNTIME_IDENTITY_SCRUB)' -ForegroundColor DarkGray
}

$auditScript = Join-Path $PSScriptRoot 'audit_profile_memories.ps1'
if (-not (Test-Path -LiteralPath $auditScript)) {
    Write-Host '[FAIL] audit_profile_memories.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}

Write-Host '--- audit_profile_memories ---' -ForegroundColor Cyan
if ($HermesRuntimeRoot) {
    & $auditScript -HermesRoot $HermesRuntimeRoot
} else {
    & $auditScript
}
if ($LASTEXITCODE -ne 0) {
    Write-Host '[FAIL] audit_profile_memories' -ForegroundColor Red
    exit 1
}

if (-not $SkipProductionGate) {
    $gatePs1 = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/audits/RUN_MEMORY_PRODUCTION_GATE.ps1'
    if (-not (Test-Path -LiteralPath $gatePs1)) {
        Write-Host '[FAIL] RUN_MEMORY_PRODUCTION_GATE.ps1 ontbreekt' -ForegroundColor Red
        exit 1
    }
    Write-Host '--- RUN_MEMORY_PRODUCTION_GATE ---' -ForegroundColor Cyan
    & $gatePs1 -RepoRoot $RepoRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[FAIL] RUN_MEMORY_PRODUCTION_GATE' -ForegroundColor Red
        exit 1
    }
}

$snippetModule = Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1'
if (-not (Test-Path -LiteralPath $snippetModule)) {
    Write-Host '[FAIL] SyncSoulSnippet.psm1 ontbreekt' -ForegroundColor Red
    exit 1
}
Import-Module $snippetModule -Force
Set-InstitutionalNewChatReminder `
    -Reason 'Memory/trust sync (USER.md, limits, SOUL)' `
    -RepoRoot $RepoRoot `
    -SmokeTestPrompt 'docs/MEMORY_ARCHITECTURE.md' `
    -Quiet:$Quiet

if (-not $Quiet) {
    Write-Host '[OK] /new-reminder gezet - TUI start automatisch een nieuwe sessie (banner + live reset)' -ForegroundColor Green
}
exit 0
