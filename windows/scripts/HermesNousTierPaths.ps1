# Tier A (Nous) vs Tier B (fork overlay) path definitions — single source for drift gates and merge policy.
# Dot-source: . (Join-Path $PSScriptRoot 'HermesNousTierPaths.ps1')

$script:HermesNousTierARoots = @(
    'agent'
    'gateway'
    'tools'
    'hermes_cli'
    'web'
    'ui-tui'
    'tui_gateway'
    'run_agent.py'
    'cli.py'
    'pyproject.toml'
    'uv.lock'
    'website'
    'docker'
)

$script:HermesNousTierAExcludePrefixes = @(
    'scripts/rag_pipeline/'
    'scripts/windows/'
    'overlay/'
    'windows/'
    'memory-bank/'
    'skills/legal/'
    'skills/productivity/landkaart/'
    'plugins/j80-windows-nl/'
    # Fork maintains its own pytest suite (upstream Linux matrix disabled on this repo).
    'tests/'
)

$script:HermesNousTierBRoots = @(
    'overlay/'
    'windows/'
    'scripts/rag_pipeline/'
    'scripts/windows/'
    'memory-bank/'
    'skills/legal/'
    'skills/productivity/landkaart/'
    'plugins/j80-windows-nl/'
    'docs/NOUS_'
    'docs/INSTITUTIONAL_'
    'docs/LEGAL_'
    'docs/domain_toolsets.yaml'
    'config/palettes.yaml'
    '.cursorrules'
    'AGENTS.md'
    'profiles/'
    '.github/workflows/fork-windows-institutional.yml'
)

# Transitional: empty when Tier A restore complete (Invoke-RestoreNousTierA.ps1).
$script:HermesNousTierATransitional = @()

# Permanent fork deltas in Tier A paths (documented; prefer overlay patch long-term).
$script:HermesNousTierAForkIntentional = @(
    'hermes_cli/gateway_windows.py'  # conda VIRTUAL_ENV in _build_gateway_cmd_script (#fork)
)

function Test-HermesPathTierAForkIntentional {
    param([Parameter(Mandatory)][string]$Path)
    $norm = ($Path -replace '\\', '/').TrimStart('./')
    return $script:HermesNousTierAForkIntentional -contains $norm
}

function Test-HermesPathUnderTierARoot {
    param([Parameter(Mandatory)][string]$Path)
    $norm = ($Path -replace '\\', '/').TrimStart('./')
    foreach ($root in $script:HermesNousTierARoots) {
        $r = ($root -replace '\\', '/').TrimEnd('/')
        if ($norm -eq $r) { return $true }
        if ($norm.StartsWith("$r/")) { return $true }
    }
    return $false
}

function Test-HermesPathTierAExcluded {
    param([Parameter(Mandatory)][string]$Path)
    $norm = ($Path -replace '\\', '/').TrimStart('./')
    foreach ($pfx in $script:HermesNousTierAExcludePrefixes) {
        if ($norm.StartsWith($pfx)) { return $true }
    }
    if ($norm.StartsWith('scripts/') -and -not $norm.StartsWith('scripts/rag_pipeline/')) {
        # scripts/* except rag_pipeline are fork helpers until moved to overlay/scripts
        if ($norm -match '^scripts/(install|run_tests|score_institutional|verify_institutional|diagnose_renderer|deduplicate|emit_codebase|bench_normalize|check-windows)') {
            return $true
        }
    }
    return $false
}

function Join-HermesForkModulePath {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$RelativePath
    )
    $rel = ($RelativePath -replace '\\', '/').TrimStart('./')
    $overlay = Join-Path $RepoRoot "overlay/$rel"
    if (Test-Path -LiteralPath $overlay) {
        return (Resolve-Path -LiteralPath $overlay).Path
    }
    return (Join-Path $RepoRoot $rel)
}

function Test-HermesForkModuleExists {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$RelativePath
    )
    return Test-Path -LiteralPath (Join-HermesForkModulePath -RepoRoot $RepoRoot -RelativePath $RelativePath)
}

function Get-HermesTierAPathSpec {
    $specs = @()
    foreach ($root in $script:HermesNousTierARoots) {
        if ($root -match '\.') {
            $specs += $root
        } else {
            $specs += "$root/"
        }
    }
    return $specs
}
