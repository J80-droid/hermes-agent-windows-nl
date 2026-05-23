<#
.SYNOPSIS
    Eén keten: team display (alle profielen) + SOUL-sync + optioneel E2E-audit.
.PARAMETER SkipE2E
    Alleen runtime toepassen, geen audit.
.PARAMETER SkipDisplay
    Alleen SOUL-sync (en eventueel E2E).
.PARAMETER SkipSoul
    Alleen display (en eventueel E2E).
.PARAMETER NoPause
    Geen pause aan het einde (ook bij aanroep via .bat).
#>
param(
    [switch]$SkipE2E,
    [switch]$SkipDisplay,
    [switch]$SkipSoul,
    [switch]$IncludeTrustRuntime,
    [switch]$NoPause
)

. (Join-Path $PSScriptRoot 'HermesShellCommon.ps1')

$ErrorActionPreference = 'Stop'
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..')).Path
Set-Location $repoRoot

Write-Host '=== Institutioneel runtime (display + SOUL) ===' -ForegroundColor Cyan

if (-not $SkipDisplay) {
    Write-Host '--- Team display (alle profielen) ---' -ForegroundColor Cyan
    & (Join-Path $scriptRoot 'apply_team_display.ps1')
    if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
}

if (-not $SkipSoul) {
    & (Join-Path $scriptRoot 'scripts\sync_soul_anatomy_snippets.ps1') -Force -RepoRoot $repoRoot
    if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
    Write-Host '[OK] SOUL anatomy snippets gesynchroniseerd (alle profielen FORCED).' -ForegroundColor Green
}

if ($IncludeTrustRuntime) {
    Write-Host '--- Trust runtime (legal template + SOUL + memory) ---' -ForegroundColor Cyan
    & (Join-Path $scriptRoot 'scripts\sync_legal_soul_from_template.ps1')
    if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
    & (Join-Path $scriptRoot 'scripts\sync_soul_anatomy_snippets.ps1') -Force -RepoRoot $repoRoot -Quiet
    if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
    & (Join-Path $scriptRoot 'scripts\sync_profile_memories.ps1')
    if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
    & (Join-Path $scriptRoot 'scripts\apply_trust_memory_limits.ps1')
    if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
    $toolSync = Join-Path $scriptRoot 'scripts\sync_profile_toolsets_from_manifest.ps1'
    if (Test-Path -LiteralPath $toolSync) {
        Write-Host '--- Domein-toolsets ---' -ForegroundColor Cyan
        & $toolSync
        if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
    }
    $apiEnvPs1 = Join-Path $scriptRoot 'sync_hermes_api_env.ps1'
    if (Test-Path -LiteralPath $apiEnvPs1) {
        Write-Host '--- API/vault .env (alle profielen) ---' -ForegroundColor Cyan
        & $apiEnvPs1
        if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
    }
    Write-Host '[OK] Trust runtime + toolsets + vault-env (geen scrub).' -ForegroundColor Green
}

if (-not $SkipE2E) {
    Write-Host '--- E2E audit ---' -ForegroundColor Cyan
    & (Join-Path $scriptRoot 'audits\RUN_INSTITUTIONAL_E2E.ps1')
    if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
}

Write-Host '=== INSTITUTIONEEL RUNTIME: KLAAR ===' -ForegroundColor Green
if (-not $SkipSoul) {
    $reminderMod = Join-Path $scriptRoot 'scripts\SyncSoulSnippet.psm1'
    if (Test-Path -LiteralPath $reminderMod) {
        Import-Module $reminderMod -Force
        Set-InstitutionalNewChatReminder -Reason 'APPLY_INSTITUTIONAL_RUNTIME (SOUL + display)' -RepoRoot $repoRoot
    } else {
        Write-Host 'Start een nieuwe chat voor SOUL/presentatie-effect.' -ForegroundColor Yellow
    }
} else {
    Write-Host 'Start een nieuwe chat na een SOUL-wijziging.' -ForegroundColor DarkYellow
}
if ($NoPause -or $env:HERMES_SKIP_PAUSE -eq '1') { exit 0 }
exit 0
