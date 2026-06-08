# Post-update finalize: pytest gates, upstream parity check, git push.
# Aangeroepen door UPDATE_HERMES.bat na drift catch-up. SSOT: docs/NOUS_DRIFT_MAINTENANCE.md
param(
    [string]$RepoRoot = '',
    [switch]$SkipForkGate,
    [switch]$SkipUpstreamReport,
    [switch]$SkipPush,
    [switch]$StrictUpstreamNewFailures,
    [switch]$IncludeProductionGate
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'HermesNousDrift.ps1')

if (-not $RepoRoot) {
    $RepoRoot = Get-HermesRepoRootFromNousScripts -Start $PSScriptRoot
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

if ($env:HERMES_SKIP_UPDATE_PUSH -eq '1') { $SkipPush = $true }
if ($env:HERMES_UPDATE_STRICT_UPSTREAM -eq '1') { $StrictUpstreamNewFailures = $true }

function Invoke-HermesPostUpdateForkGate {
    param([string]$Root)
    Write-Host '=== Post-update: pytest fork gate ===' -ForegroundColor Cyan
    $forkGate = Join-Path $Root 'windows/tests/RUN_PYTEST_FORK_GATE.bat'
    if (-not (Test-Path -LiteralPath $forkGate)) {
        Write-HermesErr "Ontbreekt: $forkGate"
        return 1
    }
    cmd /c "`"$forkGate`""
    if ($null -eq $LASTEXITCODE -or [int]$LASTEXITCODE -ne 0) {
        Write-HermesErr "Fork gate mislukt (exit $LASTEXITCODE)"
        return [int]$LASTEXITCODE
    }
    Write-HermesOk 'Fork gate geslaagd.'
    return 0
}

function Invoke-HermesPostUpdateUpstreamReport {
    param(
        [string]$Root,
        [switch]$StrictNewFailures
    )
    Write-Host '=== Post-update: upstream pytest ReportOnly ===' -ForegroundColor Cyan
    $upstreamBat = Join-Path $Root 'windows/tests/RUN_PYTEST_UPSTREAM.bat'
    if (-not (Test-Path -LiteralPath $upstreamBat)) {
        Write-HermesWarn "Ontbreekt: $upstreamBat - overgeslagen."
        return 0
    }
    cmd /c "`"$upstreamBat`" -ReportOnly"
    if ($null -eq $LASTEXITCODE -or [int]$LASTEXITCODE -ne 0) {
        Write-HermesErr "Upstream ReportOnly runner mislukt (exit $LASTEXITCODE)"
        return [int]$LASTEXITCODE
    }

    $summaryPath = Join-Path $Root 'windows/tests/pytest_upstream_summary.json'
    if (-not (Test-Path -LiteralPath $summaryPath)) {
        Write-HermesWarn "Geen $summaryPath - controleer RUN_PYTEST_UPSTREAM handmatig."
        return 0
    }
    $summary = Get-Content -LiteralPath $summaryPath -Raw -Encoding utf8 | ConvertFrom-Json
    $newCount = [int]$summary.new_failures_count
    Write-Host ("  upstream parity: new_failures_count={0} (failed={1})" -f $newCount, $summary.failed) -ForegroundColor DarkGray
    if ($newCount -gt 0) {
        $msg = "Nieuwe upstream-parity failures: $newCount - zie windows/tests/pytest_upstream_summary.json"
        if ($StrictNewFailures) {
            Write-HermesErr $msg
            return 1
        }
        Write-HermesWarn ($msg + ' (niet-blokkerend; zet HERMES_UPDATE_STRICT_UPSTREAM=1 voor hard fail)')
    } else {
        Write-HermesOk 'Upstream parity: geen nieuwe failures.'
    }
    return 0
}

function Invoke-HermesPostUpdateGitPush {
    param([string]$Root)
    Push-Location $Root
    try {
        $remotes = git remote 2>$null
        if ($remotes -notcontains 'origin') {
            Write-HermesWarn 'Geen origin-remote — push overgeslagen.'
            return 0
        }
        $branch = (git rev-parse --abbrev-ref HEAD 2>$null | Select-Object -First 1).ToString().Trim()
        if ($branch -ne 'main') {
            Write-HermesWarn ("Branch is '$branch' - push alleen naar origin/main ondersteund; overgeslagen.")
            return 0
        }
        $ahead = git rev-list --count origin/main..HEAD 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $ahead -or [int]$ahead -le 0) {
            Write-HermesOk 'Geen commits om te pushen naar origin/main.'
            return 0
        }
        Write-Host ("=== Post-update: git push origin main ({0} commit(s)) ===" -f $ahead) -ForegroundColor Cyan
        git push origin main
        if ($LASTEXITCODE -ne 0) {
            Write-HermesErr 'git push origin main mislukt.'
            return [int]$LASTEXITCODE
        }
        Write-HermesOk 'Fork op GitHub bijgewerkt (origin/main).'
        return 0
    } finally {
        Pop-Location
    }
}

function Invoke-HermesPostUpdateProductionGate {
    param([string]$Root)
    Write-Host '=== Post-update: RUN_PRODUCTION_GATE (release) ===' -ForegroundColor Cyan
    $gate = Join-Path $Root 'windows/audits/RUN_PRODUCTION_GATE.bat'
    if (-not (Test-Path -LiteralPath $gate)) {
        Write-HermesErr "Ontbreekt: $gate"
        return 1
    }
    $env:HERMES_SKIP_PAUSE_AFTER_UPDATE = '1'
    cmd /c "`"$gate`""
    if ($null -eq $LASTEXITCODE -or [int]$LASTEXITCODE -ne 0) {
        Write-HermesErr "Production gate mislukt (exit $LASTEXITCODE)"
        return [int]$LASTEXITCODE
    }
    Write-HermesOk 'Production gate geslaagd.'
    return 0
}

Write-Host ''
Write-Host '=== Hermes post-update finalize ===' -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot" -ForegroundColor DarkGray

$exitCode = 0

if (-not $SkipForkGate) {
    $rc = Invoke-HermesPostUpdateForkGate -Root $RepoRoot
    if ($rc -ne 0) { exit $rc }
}

if (-not $SkipUpstreamReport) {
    $rc = Invoke-HermesPostUpdateUpstreamReport -Root $RepoRoot -StrictNewFailures:$StrictUpstreamNewFailures
    if ($rc -ne 0) { exit $rc }
}

if ($IncludeProductionGate) {
    $rc = Invoke-HermesPostUpdateProductionGate -Root $RepoRoot
    if ($rc -ne 0) { exit $rc }
}

if (-not $SkipPush) {
    $rc = Invoke-HermesPostUpdateGitPush -Root $RepoRoot
    if ($rc -ne 0) { exit $rc }
}

Write-Host ''
Write-HermesOk 'Post-update finalize klaar.'
exit 0
