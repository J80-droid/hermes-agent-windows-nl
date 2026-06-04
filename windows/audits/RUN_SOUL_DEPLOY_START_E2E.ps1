# E2E: SOUL anatomy deploy bij start (stamp, launch-keten, POST_GIT_PULL, institutional scheiding).
param(
    [string]$RepoRoot = '',
    [switch]$SkipRuntimeAnatomy
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}
Set-Location $RepoRoot

$failures = 0
$logPath = Join-Path $scriptRoot 'SOUL_DEPLOY_START_E2E_LAST_RUN.log'

function Step-Ok {
    param([string]$Name)
    Write-HermesOk $Name
}
function Step-Fail {
    param([string]$Name, [string]$Detail)
    Write-HermesFail ($Name + ' - ' + $Detail)
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

Write-HermesSection '=== SOUL Deploy Start E2E ==='

Write-HermesSection '--- 1/8 repo-keten ---'
$required = @(
    'windows/scripts/launch_soul_anatomy_deploy.ps1',
    'windows/scripts/launch_institutional_runtime.ps1',
    'windows/scripts/sync_all_domain_souls_from_templates.ps1',
    'windows/scripts/SyncSoulSnippet.psm1',
    'windows/POST_GIT_PULL.bat',
    'windows/APPLY_SOUL_ANATOMY_RUNTIME.bat',
    'windows/launch_hermes.bat',
    'docs\SOUL_ANATOMY_SPEC.md'
)
foreach ($rel in $required) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        Step-Fail $rel 'ontbreekt'
    }
}
if ($failures -eq 0) { Step-Ok ('repo-keten: ' + $required.Count + ' bestanden') }

$analystTpl = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs\templates\SOUL_ANALYST_DOMAIN.md'
if (Test-Path -LiteralPath $analystTpl) {
    Step-Fail 'SOUL_ANALYST_DOMAIN.md' 'analyst is geen domein - template moet weg'
} else {
    Step-Ok 'geen SOUL_ANALYST_DOMAIN.md'
}

Assert-FileContains 'windows/launch_hermes.bat' @('launch_hermes.ps1')
Assert-FileContains 'windows/scripts/launch_hermes.ps1' @('launch_pre_chat_orchestrator.ps1')
Assert-FileContains 'windows/scripts/launch_pre_chat_orchestrator.ps1' @(
    'HERMES_SKIP_SOUL_DEPLOY_ON_START',
    'HERMES_SKIP_TRUST_RUNTIME_ON_START',
    'HERMES_SKIP_PENDING_TRUST_ON_START'
)
$launchBat = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/launch_hermes.bat')
$launchPs1 = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_hermes.ps1')
$orchPs1 = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_pre_chat_orchestrator.ps1')
if ($launchBat -notmatch 'launch_hermes\.ps1') {
    Step-Fail 'launch_hermes.bat' 'mist launch_hermes.ps1 entry'
} elseif ($launchPs1 -notmatch 'launch_pre_chat_orchestrator\.ps1') {
    Step-Fail 'launch_hermes.ps1' 'mist pre-chat orchestrator'
} else {
    Step-Ok 'launch_hermes.bat -> launch_hermes.ps1 -> orchestrator'
}
$soulIdx = $orchPs1.IndexOf('launch_soul_anatomy_deploy.ps1')
$trustIdx = $orchPs1.IndexOf('launch_trust_runtime_sync.ps1')
$instIdx = $orchPs1.IndexOf('launch_institutional_runtime.ps1')
$pendingIdx = $orchPs1.IndexOf('launch_pending_trust_runtime.ps1')
if ($soulIdx -lt 0 -or $instIdx -lt 0 -or $soulIdx -ge $instIdx) {
    Step-Fail 'launch_pre_chat_orchestrator.ps1' 'volgorde: soul deploy vóór institutional'
} else {
    Step-Ok 'orchestrator volgorde soul voor institutional'
}
if ($trustIdx -ge 0 -and ($trustIdx -le $soulIdx -or $trustIdx -ge $instIdx)) {
    Step-Fail 'launch_pre_chat_orchestrator.ps1' 'trust sync moet tussen soul en institutional'
} elseif ($trustIdx -ge 0) {
    Step-Ok 'orchestrator trust sync tussen soul en institutional'
}
if ($pendingIdx -lt 0 -or $instIdx -lt 0 -or $pendingIdx -le $instIdx) {
    Step-Fail 'launch_pre_chat_orchestrator.ps1' 'pending trust moet na institutional'
} else {
    Step-Ok 'orchestrator pending trust na institutional'
}

Assert-FileContains 'windows/POST_GIT_PULL.bat' @('launch_soul_anatomy_deploy.ps1', '-Force')
Assert-FileContains 'windows/APPLY_SOUL_ANATOMY_RUNTIME.bat' @('-UpdateDeployStamp')
Assert-FileContains 'windows/scripts/sync_all_domain_souls_from_templates.ps1' @('UpdateDeployStamp', 'Set-SoulAnatomyDeployStamp')

$postMerge = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/Invoke-UpstreamPostMerge.ps1'
$upstream = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/upstream_sync.ps1'
if (-not (Test-Path -LiteralPath $postMerge)) {
    Step-Fail 'Invoke-UpstreamPostMerge.ps1' 'ontbreekt'
} else {
    $pm = Get-Content -LiteralPath $postMerge -Raw -Encoding UTF8
    if ($pm -notmatch 'launch_soul_anatomy_deploy\.ps1' -or $pm -notmatch '\$soulDeployOk') {
        Step-Fail 'Invoke-UpstreamPostMerge.ps1' 'mist soul deploy + soulDeployOk SkipSoul-guard'
    } else {
        Step-Ok 'Invoke-UpstreamPostMerge.ps1 soul + conditionele SkipSoul'
    }
    if ($pm -notmatch 'Register-PendingTrustRuntimeRequired' -or $pm -notmatch 'Clear-PendingTrustRuntime') {
        Step-Fail 'Invoke-UpstreamPostMerge.ps1' 'mist pending trust stamp bij trust-fail/ok'
    } else {
        Step-Ok 'Invoke-UpstreamPostMerge.ps1 pending trust stamp'
    }
}
if (Test-Path -LiteralPath $upstream) {
    $ut = Get-Content -LiteralPath $upstream -Raw -Encoding UTF8
    if ($ut -notmatch 'Invoke-UpstreamPostMerge\.ps1') {
        Step-Fail 'upstream_sync.ps1' 'mist Invoke-UpstreamPostMerge-koppeling'
    } else {
        Step-Ok 'upstream_sync.ps1 roept Invoke-UpstreamPostMerge aan'
    }
}

Write-HermesSection '--- 2/8 stamp/watch (psm1) ---'
Import-Module (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/SyncSoulSnippet.psm1') -Force
$profiles = Get-DomainSoulProfileNames
if ($profiles.Count -ne 14) {
    Step-Fail 'Get-DomainSoulProfileNames' "verwacht 14, got $($profiles.Count)"
} else {
    Step-Ok '14 domeinprofielen'
}

$watch = Get-SoulAnatomyWatchPaths -RepoRoot $RepoRoot
if ($watch.Count -lt 15) {
    Step-Fail 'Get-SoulAnatomyWatchPaths' "te weinig paden: $($watch.Count)"
} else {
    Step-Ok "watchlist ($($watch.Count) bronnen)"
}
$legalTpl = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs\templates\SOUL_LEGAL_DOMAIN.md'
if ($legalTpl -notin $watch) {
    Step-Fail 'watchlist' 'SOUL_LEGAL_DOMAIN.md niet in watch'
} else {
    Step-Ok 'watchlist bevat legal template'
}

Write-HermesSection '--- 3/8 stamp-logica (isolated) ---'
$auditStampDir = Join-Path $env:TEMP "hermes_soul_deploy_e2e_$([Guid]::NewGuid().ToString('n'))"
New-Item -ItemType Directory -Path $auditStampDir -Force | Out-Null
try {
    $isoStamp = Join-Path $auditStampDir 'soul_anatomy_deploy.stamp'
    if (Test-SoulAnatomyDeployNeeded -RepoRoot $RepoRoot -StampPath $isoStamp) {
        Step-Ok 'geen stamp: deploy nodig'
    } else {
        Step-Fail 'stamp-logica' 'zonder stamp moet deploy nodig zijn'
    }

    Set-SoulAnatomyDeployStamp -StampPath $isoStamp
    if (-not (Test-SoulAnatomyDeployNeeded -RepoRoot $RepoRoot -StampPath $isoStamp)) {
        Step-Ok 'verse stamp: deploy niet nodig'
    } else {
        Step-Fail 'stamp-logica' 'verse stamp mag geen deploy triggeren'
    }

    $oldUtc = (Get-Date).ToUniversalTime().AddYears(-2)
    (Get-Item -LiteralPath $isoStamp).LastWriteTimeUtc = $oldUtc
    if (Test-SoulAnatomyDeployNeeded -RepoRoot $RepoRoot -StampPath $isoStamp) {
        Step-Ok 'oude stamp: deploy nodig'
    } else {
        Step-Fail 'stamp-logica' 'oude stamp moet deploy triggeren'
    }
} finally {
    Remove-Item -LiteralPath $auditStampDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-HermesSection '--- 4/8 launch_soul skip-flag ---'
$launchSoul = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_soul_anatomy_deploy.ps1'
$prevSkip = $env:HERMES_SKIP_SOUL_DEPLOY_ON_START
$env:HERMES_SKIP_SOUL_DEPLOY_ON_START = '1'
try {
    $skipOut = & $launchSoul -RepoRoot $RepoRoot *>&1 | Out-String
    if (Test-NativeCommandFailed) {
        Step-Fail 'HERMES_SKIP_SOUL_DEPLOY_ON_START' "exit $LASTEXITCODE"
    } elseif ($skipOut -notmatch 'overgeslagen') {
        Step-Fail 'HERMES_SKIP_SOUL_DEPLOY_ON_START' 'geen skip-melding'
    } else {
        Step-Ok 'HERMES_SKIP_SOUL_DEPLOY_ON_START'
    }
} finally {
    if ($null -eq $prevSkip) { Remove-Item Env:HERMES_SKIP_SOUL_DEPLOY_ON_START -ErrorAction SilentlyContinue }
    else { $env:HERMES_SKIP_SOUL_DEPLOY_ON_START = $prevSkip }
}

Write-HermesSection '--- 5/8 launch_soul up-to-date (productie-stamp) ---'
$prodStamp = Get-SoulAnatomyDeployStampPath
if (Test-Path -LiteralPath $prodStamp) {
    if (Test-SoulAnatomyDeployNeeded -RepoRoot $RepoRoot -StampPath $prodStamp) {
        Step-Ok 'productie-stamp stale (deploy bij start verwacht; geen zware sync in audit)'
    } else {
        $upOut = & $launchSoul -RepoRoot $RepoRoot -Quiet 2>&1 | Out-String
        if (Test-NativeCommandFailed) {
            Step-Fail 'launch_soul up-to-date' "exit $LASTEXITCODE"
        } elseif ($upOut -match 'Push domain') {
            Step-Fail 'launch_soul up-to-date' 'onverwachte volledige deploy'
        } elseif ($upOut -match 'up-to-date') {
            Step-Ok 'launch_soul up-to-date (stamp OK)'
        } else {
            Step-Ok 'launch_soul geen deploy (stamp vers)'
        }
    }
} else {
    Write-HermesSkip 'Geen productie-stamp - draai eerst APPLY_SOUL_ANATOMY_RUNTIME.bat'
}

Write-HermesSection '--- 6/8 institutional scheiding ---'
$instPs1 = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_institutional_runtime.ps1')
if ($instPs1 -match 'SOUL_SHARED') {
    Step-Fail 'launch_institutional_runtime.ps1' 'SOUL_SHARED hoort niet in institutional watch'
} elseif ($instPs1 -notmatch 'Test-SoulAnatomyDeployJustRan') {
    Step-Fail 'launch_institutional_runtime.ps1' 'mist Test-SoulAnatomyDeployJustRan / SkipSoul'
} else {
    Step-Ok 'institutional zonder SOUL-watch + SkipSoul na soul deploy'
}

Write-HermesSection '--- 7/8 sync_all -UpdateDeployStamp ---'
$syncText = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/sync_all_domain_souls_from_templates.ps1')
$syncHasFailedProfiles = $syncText -match 'failedProfiles'
$syncHasNativeExitTest = $syncText -match 'Test-NativeCommandFailed'
if (-not $syncHasFailedProfiles) {
    Step-Fail 'sync_all' 'mist failedProfiles'
} elseif (-not $syncHasNativeExitTest) {
    Step-Fail 'sync_all' 'mist Test-NativeCommandFailed'
} else {
    Step-Ok 'sync_all faalt bij profielfouten'
}

Write-HermesSection '--- 8/8 runtime anatomy (subset) ---'
if ($SkipRuntimeAnatomy) {
    Write-HermesSkip 'Runtime anatomy (--SkipRuntimeAnatomy)'
} else {
    & (Join-Path $scriptRoot 'RUN_SOUL_ANATOMY_E2E.ps1')
    if (Test-NativeCommandFailed) {
        Step-Fail 'RUN_SOUL_ANATOMY_E2E' 'zie output hierboven'
    } else {
        Step-Ok 'RUN_SOUL_ANATOMY_E2E (subset)'
    }
}

$summary = @(
    "SOUL Deploy Start E2E - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "Repo: $RepoRoot",
    "Failures: $failures"
)
$summary | Set-Content -LiteralPath $logPath -Encoding UTF8

Write-Host ''
if ($failures -gt 0) {
    Write-HermesFail ("SOUL Deploy Start E2E: " + $failures + " fout(en). Log: " + $logPath)
    exit 1
}
Write-HermesOk ("SOUL Deploy Start E2E: alles geslaagd. Log: " + $logPath)
exit 0
