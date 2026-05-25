# Lichte trust-runtime (memory/dedup/limits/reminder) zonder volledige SYNC_TRUST_RUNTIME.bat.
# Dot-source of aanroepen via launch_pending_trust_runtime.ps1
param(
    [Parameter(Mandatory)]
    [string]$RepoRoot,
    [switch]$SkipSoulSnippets,
    [switch]$SkipProductionGate,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot '..\HermesNativeInvoke.ps1')
Import-Module (Join-Path $PSScriptRoot 'TrustRuntimePending.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

$RepoRoot = $RepoRoot.Trim().Trim('"')
if (-not (Test-Path -LiteralPath $RepoRoot)) {
    Write-Host ('[FAIL] RepoRoot bestaat niet: ' + $RepoRoot) -ForegroundColor Red
    exit 1
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

function Write-StepLocal([string]$Msg) {
    if (-not $Quiet) {
        Write-Host ('[INFO] ' + $Msg) -ForegroundColor Cyan
    }
}
function Write-OkLocal([string]$Msg) {
    if (-not $Quiet) {
        Write-Host ('[OK] ' + $Msg) -ForegroundColor Green
    }
}
function Write-FailLocal([string]$Msg) {
    Write-Host ('[FAIL] ' + $Msg) -ForegroundColor Red
}

if (-not $PSBoundParameters.ContainsKey('SkipProductionGate')) {
    $SkipProductionGate = $true
}

$skipSnippets = $SkipSoulSnippets.IsPresent
if (-not $PSBoundParameters.ContainsKey('SkipSoulSnippets')) {
    $skipSnippets = Test-SoulAnatomyDeployJustRan -WithinSeconds 120
}

Write-StepLocal 'Trust-nazorg: geheugen, limits en chat-reminder...'

$legalPs1 = Join-Path $PSScriptRoot 'sync_legal_soul_from_template.ps1'
if (-not (Test-Path -LiteralPath $legalPs1)) {
    Write-FailLocal 'sync_legal_soul_from_template.ps1 ontbreekt'
    exit 1
}
& $legalPs1
if (Test-NativeCommandFailed) {
    Write-FailLocal 'sync_legal_soul_from_template.ps1'
    exit 1
}

if (-not $skipSnippets) {
    $snippetPs1 = Join-Path $PSScriptRoot 'sync_soul_anatomy_snippets.ps1'
    if (Test-Path -LiteralPath $snippetPs1) {
        Write-StepLocal 'SOUL snippets sync...'
        & $snippetPs1 -Force
        if (Test-NativeCommandFailed) {
            Write-FailLocal 'sync_soul_anatomy_snippets.ps1'
            exit 1
        }
    }
}

foreach ($rel in @(
        'sync_profile_memories.ps1'
        'invoke_deduplicate_memories.ps1'
        'apply_trust_memory_limits.ps1'
    )) {
    $script = Join-Path $PSScriptRoot $rel
    if (-not (Test-Path -LiteralPath $script)) {
        Write-FailLocal "Ontbreekt: $rel"
        exit 1
    }
    & $script
    if (Test-NativeCommandFailed) {
        Write-FailLocal $rel
        exit 1
    }
}

$apiBat = Join-Path $RepoRoot 'windows/SYNC_HERMES_API_ENV.bat'
if (Test-Path -LiteralPath $apiBat) {
    $prevSkipPause = $env:HERMES_SKIP_PAUSE
    $env:HERMES_SKIP_PAUSE = '1'
    try {
        & cmd /c "`"$apiBat`""
        if (Test-NativeCommandFailed) {
            Write-FailLocal 'SYNC_HERMES_API_ENV.bat'
            exit 1
        }
    } finally {
        if ($null -eq $prevSkipPause) {
            Remove-Item Env:\HERMES_SKIP_PAUSE -ErrorAction SilentlyContinue
        } else {
            $env:HERMES_SKIP_PAUSE = $prevSkipPause
        }
    }
}

$snapshotPs1 = Join-Path $PSScriptRoot 'log_trust_memory_user_snapshot.ps1'
if (Test-Path -LiteralPath $snapshotPs1) {
    & $snapshotPs1
    if (Test-NativeCommandFailed) {
        Write-FailLocal 'log_trust_memory_user_snapshot.ps1'
        exit 1
    }
}

$postSync = Join-Path $PSScriptRoot 'Invoke-MemoryTrustPostSync.ps1'
if (-not (Test-Path -LiteralPath $postSync)) {
    Write-FailLocal 'Invoke-MemoryTrustPostSync.ps1 ontbreekt'
    exit 1
}

$postArgs = @{ RepoRoot = $RepoRoot; Quiet = $Quiet }
if ($SkipProductionGate) {
    $postArgs['SkipProductionGate'] = $true
}
& $postSync @postArgs
if (Test-NativeCommandFailed -or ($null -ne $LASTEXITCODE -and [int]$LASTEXITCODE -ne 0)) {
    Write-FailLocal 'Invoke-MemoryTrustPostSync.ps1'
    exit 1
}

Clear-PendingTrustRuntime
Write-OkLocal 'Trust-nazorg klaar. Hermes opent zo - nieuwe chat wordt automatisch gestart.'
exit 0
