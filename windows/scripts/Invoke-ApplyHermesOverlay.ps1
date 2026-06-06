# Post-merge overlay apply: bootstrap env, optional extras install, UI build hook.
param(
    [Parameter(Mandatory)]
    [string]$RepoRoot,
    [switch]$SkipRagExtras,
    [switch]$SkipUiBuild,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Invoke-HermesOverlayBootstrap.ps1')
Invoke-HermesOverlayBootstrap -RepoRoot $RepoRoot

$extras = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/pyproject.extras.toml'
if (-not $SkipRagExtras -and (Test-Path -LiteralPath $extras)) {
    $ragPs1 = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/install_rag_extras.ps1'
    if (Test-Path -LiteralPath $ragPs1) {
        if (-not $Quiet) { Write-Host '[INFO] overlay extras (rag/voice-windows)...' -ForegroundColor Cyan }
        & $ragPs1 -RepoRoot $RepoRoot
    }
}

$uiBuild = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/build_fork_ui_assets.ps1'
if (-not $SkipUiBuild -and (Test-Path -LiteralPath $uiBuild)) {
    if (-not $Quiet) { Write-Host '[INFO] fork UI overlay build (no-op if deps missing)...' -ForegroundColor Cyan }
    & $uiBuild -RepoRoot $RepoRoot
}

if (-not $Quiet) { Write-Host '[OK] Overlay apply finished.' -ForegroundColor Green }
