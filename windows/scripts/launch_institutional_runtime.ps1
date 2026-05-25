# Institutioneel runtime vóór Hermes-chat: display (alle profielen) + SOUL-snippet-sync indien nodig.
# Volledige SOUL anatomy (13 templates) gebeurt in launch_soul_anatomy_deploy.ps1.
# E2E alleen met -RunE2E of HERMES_INSTITUTIONAL_E2E_ON_START=1 (traag; niet standaard).
param(
    [string]$RepoRoot = '',
    [switch]$RunE2E,
    [switch]$Force,
    [switch]$SkipConfigDrift
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'HermesHomeCommon.ps1')
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

if (-not $RepoRoot -and $env:HERMES_REPO_ROOT) {
    $RepoRoot = $env:HERMES_REPO_ROOT
}
if ($RepoRoot) {
    $RepoRoot = $RepoRoot.Trim().Trim('"')
}
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} elseif (-not (Test-Path -LiteralPath $RepoRoot)) {
    Write-Host ('ERROR: RepoRoot bestaat niet: ' + $RepoRoot) -ForegroundColor Red
    exit 1
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

if ($env:HERMES_SKIP_INSTITUTIONAL_RUNTIME -eq '1') {
    Write-Host '[INFO] Institutioneel runtime overgeslagen (HERMES_SKIP_INSTITUTIONAL_RUNTIME=1).' -ForegroundColor DarkGray
    exit 0
}

$runE2e = $RunE2E.IsPresent -or $env:HERMES_INSTITUTIONAL_E2E_ON_START -eq '1'
if (-not $SkipConfigDrift) {
    if ($runE2e) {
        if (-not (Test-HermesConfigDrift -Strict)) {
            Write-Host '[FAIL] Config split-home drift (E2E) — APPLY_HERMES_HOME_MIGRATION.bat' -ForegroundColor Red
            exit 1
        }
    } else {
        Test-HermesConfigDrift | Out-Null
    }
}

$stampDir = Get-HermesRoot
$stampFile = Join-Path $stampDir 'launch_institutional_runtime.stamp'

$watchFiles = @(
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/team_display.defaults'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/apply_team_display_profiles.py'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/apply_institutional_runtime.ps1')
) | Where-Object { Test-Path -LiteralPath $_ }

$needRun = $Force.IsPresent -or $runE2e
if (-not $needRun -and (Test-Path -LiteralPath $stampFile) -and $watchFiles.Count -gt 0) {
    $stampTime = (Get-Item -LiteralPath $stampFile).LastWriteTimeUtc
    foreach ($f in $watchFiles) {
        if ((Get-Item -LiteralPath $f).LastWriteTimeUtc -gt $stampTime) {
            $needRun = $true
            break
        }
    }
} elseif (-not (Test-Path -LiteralPath $stampFile)) {
    $needRun = $true
}

if (-not $needRun) {
    $driftScript = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/apply_team_display_profiles.py'
    if (Test-Path -LiteralPath $driftScript) {
        $env:HERMES_ROOT = $stampDir
        $env:PYTHONPATH = $RepoRoot
        $driftPy = $null
        foreach ($candidate in @(
                (Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'),
                (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python312\python.exe'),
                'python'
            )) {
            if ($candidate -eq 'python' -or (Test-Path -LiteralPath $candidate)) {
                $driftPy = $candidate
                break
            }
        }
        if ($driftPy) {
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            & $driftPy $driftScript --check-drift 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) {
                $needRun = $true
                Write-Host '[INFO] Team display drift gedetecteerd — apply opnieuw gepland.' -ForegroundColor Yellow
            }
            $ErrorActionPreference = $prevEap
        }
    }
}

if (-not $needRun) {
    Write-Host '[INFO] Institutioneel runtime up-to-date (stamp OK).' -ForegroundColor DarkGray
    exit 0
}

$runtimePs1 = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/apply_institutional_runtime.ps1'
$runtimeArgs = @{ SkipE2E = (-not $runE2e); NoPause = $true }
if (Test-SoulAnatomyDeployJustRan) {
    $runtimeArgs['SkipSoul'] = $true
}

Write-Host '[INFO] Institutioneel runtime (display' -NoNewline -ForegroundColor Cyan
if (-not $runtimeArgs['SkipSoul']) { Write-Host ' + SOUL snippets' -NoNewline -ForegroundColor Cyan }
if ($runE2e) { Write-Host ' + E2E' -NoNewline -ForegroundColor Cyan }
Write-Host ')...' -ForegroundColor Cyan

& $runtimePs1 @runtimeArgs
if (Test-NativeCommandFailed) { exit $LASTEXITCODE }

if (-not (Test-Path -LiteralPath $stampDir)) {
    New-Item -ItemType Directory -Path $stampDir -Force | Out-Null
}
$utf8 = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($stampFile, (Get-Date -Format 'o'), $utf8)
Write-Host '[OK] Institutioneel runtime toegepast.' -ForegroundColor Green

$noticeFile = Join-Path $stampDir 'institutional_new_chat_required.json'
if (Test-Path -LiteralPath $noticeFile) {
    Write-Host '[HERINNERING] SOUL/presentatie is bijgewerkt — gebruik /new of een nieuwe sessie.' -ForegroundColor Yellow
    Write-Host '  Rooktest: docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md' -ForegroundColor DarkYellow
}
exit 0
