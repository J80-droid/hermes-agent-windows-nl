# One-shot: copy fork-only Tier A additions to overlay, then restore upstream/main on Tier A trees.
param(
    [string]$RepoRoot = '',
    [string]$UpstreamRef = 'upstream/main'
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'HermesNousTierPaths.ps1')

function Get-RepoRoot {
    param([string]$Start)
    $d = if ($Start) { $Start } else { $PSScriptRoot }
    while ($d) {
        if ((Test-Path (Join-Path $d 'pyproject.toml')) -and (Test-Path (Join-Path $d 'cli.py'))) {
            return (Resolve-Path -LiteralPath $d).Path
        }
        $next = Split-Path -Parent $d
        if (-not $next -or $next -eq $d) { break }
        $d = $next
    }
    throw 'Repo root not found'
}

function Copy-ForkAdditionToOverlay {
    param(
        [string]$Repo,
        [string]$RelativePath
    )
    $src = Join-Path $Repo $RelativePath
    if (-not (Test-Path -LiteralPath $src)) { return }
    $dst = Join-Path $Repo ('overlay/' + ($RelativePath -replace '\\', '/'))
    $dstDir = Split-Path -Parent $dst
    if (-not (Test-Path -LiteralPath $dstDir)) {
        New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    }
    if (-not (Test-Path -LiteralPath $dst)) {
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }
}

$repo = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { Get-RepoRoot -Start $PSScriptRoot }
Push-Location $repo
try {
    $ErrorActionPreference = 'Continue'
    git fetch upstream 2>&1 | Out-Null
    $ErrorActionPreference = 'Stop'

    $specs = @('agent/', 'hermes_cli/', 'web/', 'ui-tui/')
    foreach ($spec in $specs) {
        $added = @(git diff --name-only --diff-filter=A $UpstreamRef -- $spec 2>$null | Where-Object { $_.Trim() })
        foreach ($p in $added) {
            Copy-ForkAdditionToOverlay -Repo $repo -RelativePath $p
        }
    }

    $restorePaths = @(
        'agent',
        'gateway',
        'tools',
        'hermes_cli',
        'web',
        'ui-tui',
        'tui_gateway',
        'cli.py',
        'run_agent.py',
        'pyproject.toml',
        'uv.lock',
        'website',
        'docker'
    )
    Write-Host "[INFO] git checkout $UpstreamRef -- $($restorePaths -join ' ')" -ForegroundColor Cyan
    git checkout $UpstreamRef -- @restorePaths
    if ($LASTEXITCODE -ne 0) { throw "git checkout failed ($LASTEXITCODE)" }

    foreach ($prefix in @('agent', 'hermes_cli', 'web', 'ui-tui', 'gateway', 'tools', 'tui_gateway')) {
        $up = @(git ls-tree -r --name-only $UpstreamRef -- "${prefix}/" 2>$null)
        $upSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach ($u in $up) { [void]$upSet.Add($u) }
        foreach ($f in @(git ls-files "${prefix}/" 2>$null)) {
            if (-not $upSet.Contains($f)) {
                git rm -f --cached $f 2>$null | Out-Null
                if (Test-Path -LiteralPath $f) { Remove-Item -Force -LiteralPath $f }
            }
        }
    }

    Write-Host '[OK] Tier A trees restored from upstream (extras removed).' -ForegroundColor Green
} finally {
    Pop-Location
}
