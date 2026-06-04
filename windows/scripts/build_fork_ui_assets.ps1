# Optional: build web/tui with overlay paths. No-op when npm/vite unavailable.
param([string]$RepoRoot = '')
$ErrorActionPreference = 'Continue'
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}
Write-Host '[INFO] build_fork_ui_assets: overlay/vite aliases documented in NOUS_OVERLAY_ARCHITECTURE.md (skip build).' -ForegroundColor DarkGray
exit 0
