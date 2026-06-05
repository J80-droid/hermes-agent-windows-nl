# Copy overlay/web and overlay/ui-tui sources into Tier A trees for local build only.
param(
    [Parameter(Mandatory)]
    [string]$RepoRoot,
    [ValidateSet('web', 'ui-tui', 'all')]
    [string]$Target = 'all'
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

function Copy-OverlayTree {
    param(
        [string]$OverlaySrc,
        [string]$DestRoot
    )
    if (-not (Test-Path -LiteralPath $OverlaySrc)) {
        return 0
    }
    $overlayRoot = (Resolve-Path -LiteralPath $OverlaySrc).Path.TrimEnd('\', '/')
    $destRoot = (Resolve-Path -LiteralPath $DestRoot).Path.TrimEnd('\', '/')
    $n = 0
    Get-ChildItem -LiteralPath $overlayRoot -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($overlayRoot.Length).TrimStart('\', '/')
        $dest = Join-Path $destRoot $rel
        $parent = Split-Path -Parent $dest
        if (-not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        if (-not (Test-Path -LiteralPath $dest) -or $_.LastWriteTimeUtc -gt (Get-Item -LiteralPath $dest).LastWriteTimeUtc) {
            Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
            $script:n++
        }
    }
    return $n
}

$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$copied = 0

if ($Target -eq 'all' -or $Target -eq 'web') {
    $from = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/web/src'
    $to = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'web/src'
    if (Test-Path -LiteralPath $from) {
        $nWeb = Copy-OverlayTree -OverlaySrc $from -DestRoot $to
        $copied += $nWeb
        Write-Host "[OK] overlay/web/src -> web/src ($nWeb files)" -ForegroundColor Green
    }
}

if ($Target -eq 'all' -or $Target -eq 'ui-tui') {
    $from = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/ui-tui/src'
    $to = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'ui-tui/src'
    if (Test-Path -LiteralPath $from) {
        $n = Copy-OverlayTree -OverlaySrc $from -DestRoot $to
        $copied += $n
        Write-Host "[OK] overlay/ui-tui/src -> ui-tui/src ($n files)" -ForegroundColor Green
    }
}

if ($copied -eq 0) {
    Write-Host '[INFO] Geen overlay-bronbestanden gekopieerd (al up-to-date of ontbrekend).' -ForegroundColor DarkGray
}
exit 0
