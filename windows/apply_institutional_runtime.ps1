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

$ErrorActionPreference = 'Stop'
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..')).Path
Set-Location $repoRoot

Write-Host '=== Institutioneel runtime (display + SOUL) ===' -ForegroundColor Cyan

if (-not $SkipDisplay) {
    Write-Host '--- Team display (alle profielen) ---' -ForegroundColor Cyan
    & (Join-Path $scriptRoot 'apply_team_display.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipSoul) {
    Write-Host '--- SOUL Interaction ---' -ForegroundColor Cyan
    & (Join-Path $scriptRoot 'scripts\sync_soul_interaction_snippet.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host '--- SOUL Outputformaat ---' -ForegroundColor Cyan
    & (Join-Path $scriptRoot 'scripts\sync_soul_output_format_snippet.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host '[OK] SOUL Interaction + Outputformaat gesynchroniseerd.' -ForegroundColor Green
}

if ($IncludeTrustRuntime) {
    Write-Host '--- Trust runtime (advisory + legal + memory) ---' -ForegroundColor Cyan
    & (Join-Path $scriptRoot 'scripts\sync_legal_soul_from_template.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & (Join-Path $scriptRoot 'scripts\sync_soul_advisory_snippet.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & (Join-Path $scriptRoot 'scripts\sync_profile_memories.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & (Join-Path $scriptRoot 'scripts\apply_trust_memory_limits.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host '[OK] Trust runtime (geen scrub).' -ForegroundColor Green
}

if (-not $SkipE2E) {
    Write-Host '--- E2E audit ---' -ForegroundColor Cyan
    & (Join-Path $scriptRoot 'audits\RUN_INSTITUTIONAL_E2E.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host '=== INSTITUTIONEEL RUNTIME: KLAAR ===' -ForegroundColor Green
Write-Host 'Start een nieuwe chat voor SOUL/presentatie-effect.' -ForegroundColor Yellow
if ($NoPause -or $env:HERMES_SKIP_PAUSE -eq '1') { exit 0 }
exit 0
