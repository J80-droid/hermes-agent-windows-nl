# Build web/tui with overlay sources merged into src (Tier B; restores src after each target).
param(
    [string]$RepoRoot = '',
    [switch]$SkipWeb,
    [switch]$SkipTui,
    [switch]$KeepMergedSrc
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$copyPs1 = Join-Path $PSScriptRoot 'Invoke-CopyHermesOverlaySources.ps1'
if (-not (Test-Path -LiteralPath $copyPs1)) {
    Write-Host '[FAIL] Invoke-CopyHermesOverlaySources.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}

$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    Write-Host '[WARN] npm niet op PATH — overlay UI build overgeslagen.' -ForegroundColor Yellow
    exit 0
}

function Restore-TierASrc {
    param([string]$RelativePath)
    if ($KeepMergedSrc) { return }
    Push-Location $RepoRoot
    try {
        if (Test-Path -LiteralPath $RelativePath) {
            git checkout -- $RelativePath 2>$null
        }
    } finally {
        Pop-Location
    }
}

if (-not $SkipTui) {
    $tuiMerged = $false
    try {
        & $copyPs1 -RepoRoot $RepoRoot -Target 'ui-tui'
        $tuiMerged = $true
        $rebuild = Join-Path $PSScriptRoot 'rebuild_tui.ps1'
        if (Test-Path -LiteralPath $rebuild) {
            & $rebuild -RepoRoot $RepoRoot -Force
            if ($LASTEXITCODE -ne 0) {
                throw "rebuild_tui.ps1 exit $LASTEXITCODE"
            }
        }
    } finally {
        if ($tuiMerged) {
            Restore-TierASrc -RelativePath 'ui-tui/src'
        }
    }
}

if (-not $SkipWeb) {
    $webMerged = $false
    try {
        & $copyPs1 -RepoRoot $RepoRoot -Target 'web'
        $webMerged = $true
        $webDir = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'web'
        $webPkg = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'web/package.json'
        if (Test-Path -LiteralPath $webPkg) {
            Push-Location $webDir
            try {
                & npm run build --silent
                if ($LASTEXITCODE -ne 0) {
                    throw "web npm run build exit $LASTEXITCODE"
                }
                Write-Host '[OK] web -> hermes_cli/web_dist' -ForegroundColor Green
            } finally {
                Pop-Location
            }
        }
    } finally {
        if ($webMerged) {
            Restore-TierASrc -RelativePath 'web/src'
        }
    }
}

Write-Host '[OK] build_fork_ui_assets voltooid.' -ForegroundColor Green
exit 0
