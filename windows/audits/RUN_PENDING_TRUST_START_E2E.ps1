# E2E: pending trust-runtime bij Hermes-start (stamp, launcher, post-merge, lichte keten).
# Syntax-check: windows/tests/Validate-AuditPs1Syntax.ps1
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot '..\HermesNativeInvoke.ps1')

$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}
Set-Location $RepoRoot

$failures = 0
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$logPath = Join-Path $scriptRoot ('PENDING_TRUST_START_E2E_REPORT_' + $reportStamp + '.md')

function Step-Ok { param([string]$Name) Write-Host ('[OK] ' + $Name) -ForegroundColor Green }
function Step-Fail {
    param([string]$Name, [string]$Detail)
    Write-Host ('[FAIL] ' + $Name + ' - ' + $Detail) -ForegroundColor Red
    $script:failures++
}

function Assert-FileContains {
    param(
        [string]$RelPath,
        [string[]]$MustContain,
        [string[]]$MustNotContain = @()
    )
    $full = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $RelPath
    if (-not (Test-Path -LiteralPath $full)) {
        Step-Fail $RelPath 'bestand ontbreekt'
        return
    }
    $text = Get-Content -LiteralPath $full -Raw -Encoding UTF8
    foreach ($needle in $MustContain) {
        if ($text -notmatch [regex]::Escape($needle)) {
            Step-Fail $RelPath "mist: $needle"
            return
        }
    }
    foreach ($bad in $MustNotContain) {
        if ($text -match [regex]::Escape($bad)) {
            Step-Fail $RelPath "mag niet bevatten: $bad"
            return
        }
    }
    Step-Ok $RelPath
}

Write-Host '=== Pending Trust Start E2E ===' -ForegroundColor Cyan

Write-Host '--- 1/5 repo-keten ---' -ForegroundColor Cyan
$required = @(
    'windows/scripts/TrustRuntimePending.psm1',
    'windows/scripts/Invoke-TrustRuntimeLight.ps1',
    'windows/scripts/launch_pending_trust_runtime.ps1',
    'windows/scripts/Invoke-UpstreamPostMerge.ps1',
    'windows/launch_hermes.bat',
    'windows/SYNC_TRUST_RUNTIME.bat',
    'docs/TRUST_FORENSIC_PROTOCOL.md',
    'docs/HERMES_START.md'
)
foreach ($rel in $required) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        Step-Fail $rel 'ontbreekt'
    }
}
if ($failures -eq 0) { Step-Ok ('repo-keten: ' + $required.Count + ' bestanden') }

Assert-FileContains 'windows/launch_hermes.bat' @('launch_hermes.ps1')
Assert-FileContains 'windows/scripts/launch_hermes.ps1' @('launch_pre_chat_orchestrator.ps1')
Assert-FileContains 'windows/scripts/launch_pre_chat_orchestrator.ps1' @(
    'launch_pending_trust_runtime.ps1',
    'HERMES_SKIP_PENDING_TRUST_ON_START'
)
$launchBat = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/launch_hermes.bat')
$launchPs1 = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_hermes.ps1')
$orchPs1 = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_pre_chat_orchestrator.ps1')
if ($launchBat -notmatch 'launch_hermes\.ps1') {
    Step-Fail 'launch_hermes.bat' 'mist launch_hermes.ps1 entry'
} elseif ($launchPs1 -notmatch 'launch_pre_chat_orchestrator\.ps1') {
    Step-Fail 'launch_hermes.ps1' 'mist pending trust orchestrator'
} elseif ($orchPs1 -notmatch 'launch_pending_trust_runtime\.ps1') {
    Step-Fail 'launch_pre_chat_orchestrator.ps1' 'mist pending trust fase'
} else {
    $instIdx = $orchPs1.IndexOf('launch_institutional_runtime.ps1')
    $pendingIdx = $orchPs1.IndexOf('launch_pending_trust_runtime.ps1')
    if ($pendingIdx -le $instIdx) {
        Step-Fail 'launch_pre_chat_orchestrator.ps1' 'pending trust moet na institutional runtime'
    } else {
        Step-Ok 'launch-keten volgorde pending na institutional'
    }
}

$postMerge = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/Invoke-UpstreamPostMerge.ps1')
if ($postMerge -notmatch 'Register-PendingTrustRuntimeRequired' -or $postMerge -notmatch 'Clear-PendingTrustRuntime') {
    Step-Fail 'Invoke-UpstreamPostMerge.ps1' 'mist pending trust stamp'
} else {
    Step-Ok 'Invoke-UpstreamPostMerge.ps1 pending stamp'
}

Assert-FileContains 'windows/scripts/Invoke-TrustRuntimeLight.ps1' @(
    'Invoke-MemoryTrustPostSync.ps1',
    'Clear-PendingTrustRuntime',
    'SkipProductionGate'
)
Assert-FileContains 'windows/scripts/launch_pending_trust_runtime.ps1' @(
    'Invoke-TrustRuntimeLight.ps1',
    'HERMES_PENDING_TRUST_E2E_DRY_RUN',
    'Clear-StalePendingTrustRuntimeFile'
)

Write-Host '--- 2/5 geïsoleerde module + launcher ---' -ForegroundColor Cyan
$isoRoot = Join-Path $env:TEMP ('hermes_pending_trust_e2e_' + [Guid]::NewGuid().ToString('n'))
$isoHermes = Join-Path $isoRoot 'hermes'
$corePath = Join-Path $scriptRoot 'PendingTrustStartE2E.core.ps1'
& $corePath -RepoRoot $RepoRoot -IsolatedHermesDir $isoHermes
$coreFailures = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
if ($coreFailures -gt 0) {
    $failures += $coreFailures
    Step-Fail 'PendingTrustStartE2E.core.ps1' "$coreFailures stap(pen) gefaald"
} else {
    Step-Ok 'PendingTrustStartE2E.core.ps1'
}

Write-Host '--- 3/5 pytest wiring ---' -ForegroundColor Cyan
if ($SkipPytest) {
    Step-Ok 'pytest overgeslagen (-SkipPytest)'
} else {
    $python = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        Step-Fail 'pytest' "python niet gevonden: $python"
    } else {
        $env:PYTHONPATH = $RepoRoot
        & $python -m pytest tests/windows/test_pending_trust_runtime.py -q --tb=no
        if ($LASTEXITCODE -ne 0) {
            Step-Fail 'test_pending_trust_runtime.py' "exit $LASTEXITCODE"
        } else {
            Step-Ok 'test_pending_trust_runtime.py'
        }
    }
}

Write-Host '--- 4/5 syntax parse ---' -ForegroundColor Cyan
$parseTargets = @(
    'windows/scripts/TrustRuntimePending.psm1',
    'windows/scripts/Invoke-TrustRuntimeLight.ps1',
    'windows/scripts/launch_pending_trust_runtime.ps1',
    'windows/audits/PendingTrustStartE2E.core.ps1',
    'windows/audits/RUN_PENDING_TRUST_START_E2E.ps1'
)
foreach ($rel in $parseTargets) {
    $path = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel
    $parseErr = [System.Collections.Generic.List[object]]::new()
    $null = [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$parseErr)
    if ($parseErr.Count -gt 0) {
        Step-Fail $rel ($parseErr[0].Message)
    }
}
if ($failures -eq 0) { Step-Ok 'PS1 syntax parse' }

Write-Host '--- 5/5 rapport ---' -ForegroundColor Cyan
$summary = @(
    '# Pending Trust Start E2E',
    '',
    "- Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "- Repo: $RepoRoot",
    "- Failures: $failures",
    '',
    'Scenario''s: repo-keten, post-merge stamp, launch-volgorde, module lifecycle, stale cleanup, skip-flag, max attempts, dry-run launcher, pytest.'
)
$summary | Set-Content -LiteralPath $logPath -Encoding UTF8
Step-Ok ('rapport: ' + (Split-Path -Leaf $logPath))

Write-Host ''
if ($failures -gt 0) {
    Write-Host ("=== Pending Trust Start E2E FAIL ($failures) ===") -ForegroundColor Red
    exit 1
}
Write-Host '=== Pending Trust Start E2E PASS ===' -ForegroundColor Green
exit 0
