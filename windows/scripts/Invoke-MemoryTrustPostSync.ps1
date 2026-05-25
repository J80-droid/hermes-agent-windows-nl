# Na SYNC_TRUST_RUNTIME: Repair-HermesRuntimeIdentity (tenzij HERMES_SKIP_RUNTIME_IDENTITY_SCRUB),
# audit_profile_memories, optioneel RUN_MEMORY_PRODUCTION_GATE, inline institutional_new_chat_required.json.
# Dot-source HermesShellCommon vóór MemoryAuditCommon. Zie docs/TRUST_FORENSIC_PROTOCOL.md.
param(
    [string]$RepoRoot = '',
    [string]$HermesRuntimeRoot = '',
    [switch]$SkipProductionGate,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$skipScrubValues = @('1', 'true', 'True', 'yes', 'Yes')
$scrubEnv = [string]$env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB
if ($skipScrubValues -notcontains $scrubEnv) {
    . (Join-Path $PSScriptRoot 'MemoryAuditCommon.ps1')
    if (-not $Quiet) {
        Write-HermesInfo 'Repair-HermesRuntimeIdentity (pre-audit)'
    }
    if ($HermesRuntimeRoot) {
        if ($Quiet) {
            $scrubResult = Repair-HermesRuntimeIdentity -HermesRoot $HermesRuntimeRoot -Quiet
        } else {
            $scrubResult = Repair-HermesRuntimeIdentity -HermesRoot $HermesRuntimeRoot
        }
    } elseif ($Quiet) {
        $scrubResult = Repair-HermesRuntimeIdentity -Quiet
    } else {
        $scrubResult = Repair-HermesRuntimeIdentity
    }
    if (-not $Quiet -and $scrubResult.FilesChanged -eq 0) {
        Write-HermesInfo 'Runtime identity: geen wijzigingen nodig'
    }
} elseif (-not $Quiet) {
    Write-HermesInfo 'Runtime identity scrub overgeslagen (HERMES_SKIP_RUNTIME_IDENTITY_SCRUB)'
}

$auditScript = Join-Path $PSScriptRoot 'audit_profile_memories.ps1'
if (-not (Test-Path -LiteralPath $auditScript)) {
    Write-HermesFail 'audit_profile_memories.ps1 ontbreekt'
    exit 1
}

Write-HermesInfo 'audit_profile_memories'
if ($HermesRuntimeRoot) {
    & $auditScript -HermesRoot $HermesRuntimeRoot
} else {
    & $auditScript
}
if (Test-NativeCommandFailed) {
    Write-HermesFail 'audit_profile_memories'
    exit 1
}

if (-not $SkipProductionGate) {
    $gateScript = Join-Path $RepoRoot 'windows\audits\RUN_MEMORY_PRODUCTION_GATE.ps1'
    if (-not (Test-Path -LiteralPath $gateScript)) {
        Write-HermesFail 'RUN_MEMORY_PRODUCTION_GATE.ps1 ontbreekt'
        exit 1
    }
    Write-HermesInfo 'RUN_MEMORY_PRODUCTION_GATE'
    & $gateScript -RepoRoot $RepoRoot
    if (Test-NativeCommandFailed) {
        Write-HermesFail 'RUN_MEMORY_PRODUCTION_GATE'
        exit 1
    }
}

$smokeRel = Join-Path 'docs' 'MEMORY_ARCHITECTURE.md'
$hermesDir = Join-Path $env:LOCALAPPDATA 'hermes'
if (-not (Test-Path -LiteralPath $hermesDir)) {
    New-Item -ItemType Directory -Path $hermesDir -Force | Out-Null
}
$noticePath = Join-Path $hermesDir 'institutional_new_chat_required.json'
$noticePayload = @{
    required_at       = (Get-Date -Format 'o')
    reason            = 'Memory-trust sync'
    smoke_test_prompt = $smokeRel
    repo_root         = $RepoRoot
}
try {
    $noticePayload | ConvertTo-Json | Set-Content -LiteralPath $noticePath -Encoding UTF8
} catch {
    Write-HermesFail ('Kon institutional_new_chat_required.json niet schrijven: ' + $_.Exception.Message)
    exit 1
}
if (-not $Quiet -and $env:HERMES_SUPPRESS_SOUL_REMINDER -ne '1') {
    Write-HermesWarn ('Start een nieuwe chat (slash-new). Rooktest: ' + $smokeRel)
}
if (-not $Quiet) {
    Write-HermesOk 'new-reminder gezet - TUI start automatisch een nieuwe sessie (banner + live reset)'
}
exit 0
