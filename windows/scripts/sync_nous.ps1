# SYNC_NOUS: merge upstream/main → apply overlay → drift gate → post-merge chain.
# See docs/NOUS_OVERLAY_ARCHITECTURE.md
param(
    [ValidateSet('Preflight', 'Merge', 'Apply', 'Verify', 'PostMerge', 'Full')]
    [string]$Phase = 'Full',
    [string]$RepoRoot = '',
    [switch]$Force,
    [switch]$AllowDirty,
    [switch]$AllowTransitionalDrift,
    [switch]$SkipMerge,
    [switch]$SkipPush,
    [switch]$Push,
    [switch]$Yes
)

$script:SyncNousForce = [bool]$Force
$script:SyncNousAllowDirty = [bool]$AllowDirty
$script:SyncNousAllowTransitionalDrift = [bool]$AllowTransitionalDrift
$script:SyncNousSkipMerge = [bool]$SkipMerge
$script:SyncNousSkipPush = [bool]$SkipPush
$script:SyncNousPush = [bool]$Push
$script:SyncNousYes = [bool]$Yes

$ErrorActionPreference = 'Stop'
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'HermesNousTierPaths.ps1')

function Get-HermesRepoRootLocal {
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

$repo = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { Get-HermesRepoRootLocal -Start $PSScriptRoot }
$upstreamRef = 'upstream/main'

function Invoke-SyncNousPreflight {
    $guard = Join-HermesRepoPath -RepoRoot $repo -RelativePath 'windows/scripts/guard_git_clean.ps1'
    if ((Test-Path -LiteralPath $guard) -and -not $script:SyncNousAllowDirty) {
        & $guard -Quiet
        if ($LASTEXITCODE -eq 2) { exit 2 }
    }
    git -C $repo fetch upstream 2>&1 | Out-Null
}

function Invoke-SyncNousMerge {
    if ($script:SyncNousSkipMerge) { return }
    $syncPs1 = Join-HermesRepoPath -RepoRoot $repo -RelativePath 'windows/upstream_sync.ps1'
    if (-not (Test-Path -LiteralPath $syncPs1)) { throw "Missing $syncPs1" }
    $mergeArgs = @('-Phase', 'Update', '-RepoRoot', $repo)
    if ($script:SyncNousForce) { $mergeArgs += '-Force' }
    if ($script:SyncNousAllowDirty) { $mergeArgs += '-AllowDirty' }
    if ($script:SyncNousYes) { $env:HERMES_UPSTREAM_AUTO_CONFIRM = '1' }
    & $syncPs1 @mergeArgs
    $rc = $LASTEXITCODE
    if ($rc -ne 0) { exit $rc }
}

function Invoke-SyncNousApply {
    $apply = Join-HermesRepoPath -RepoRoot $repo -RelativePath 'windows/scripts/Invoke-ApplyHermesOverlay.ps1'
    & $apply -RepoRoot $repo
}

function Invoke-SyncNousVerify {
    $test = Join-HermesRepoPath -RepoRoot $repo -RelativePath 'windows/scripts/Test-NousTreeIdentical.ps1'
    $testArgs = @{ RepoRoot = $repo; UpstreamRef = $upstreamRef }
    if ($script:SyncNousAllowTransitionalDrift) { $testArgs['AllowTransitional'] = $true }
    & $test @testArgs
    return $LASTEXITCODE
}

function Invoke-SyncNousPostMerge {
    $post = Join-HermesRepoPath -RepoRoot $repo -RelativePath 'windows/scripts/Invoke-UpstreamPostMerge.ps1'
    if (Test-Path -LiteralPath $post) {
        . $post
        $null = Invoke-UpstreamPostMerge -RepoRoot $repo
    }
}

function Invoke-SyncNousPushOrigin {
    if ($script:SyncNousSkipPush -and -not $script:SyncNousPush) { return }
    if (-not $script:SyncNousPush -and -not $script:SyncNousYes) { return }
    git -C $repo push origin HEAD 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Warning 'git push origin failed' }
}

switch ($Phase) {
    'Preflight' { Invoke-SyncNousPreflight; exit 0 }
    'Merge' { Invoke-SyncNousPreflight; Invoke-SyncNousMerge; exit $LASTEXITCODE }
    'Apply' { Invoke-SyncNousApply; exit 0 }
    'Verify' { exit (Invoke-SyncNousVerify) }
    'PostMerge' { Invoke-SyncNousPostMerge; exit 0 }
    'Full' {
        Invoke-SyncNousPreflight
        Invoke-SyncNousMerge
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Invoke-SyncNousApply
        Invoke-SyncNousPostMerge
        $v = Invoke-SyncNousVerify
        Invoke-SyncNousPushOrigin
        exit $v
    }
}
