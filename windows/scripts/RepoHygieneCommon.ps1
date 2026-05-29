# Gedeelde repo-root hygiene helpers (guard + QuickFix).

function Get-HermesRepoRootAllowlist {
    return @(
        '.gitignore', '.cursorrules', '.env', '.pre-commit-config.yaml', 'pyproject.toml', 'package.json',
        'uv.lock', 'README.md', 'README-FORK.md', 'README.zh-CN.md',
        'AGENTS.md', 'cli.py', 'run_agent.py', 'model_tools.py', 'toolsets.py',
        'hermes_state.py', 'hermes_constants.py', 'hermes_logging.py',
        'hermes_bootstrap.py', 'hermes_time.py', 'batch_runner.py', 'config.yaml',
        'hermes_launch.log', 'hermes_runtime.log', 'hermes_last_error.log', 'hermes_setup.log'
    )
}

function Resolve-HermesAgentRepoRoot {
    param([string]$StartDir = $PSScriptRoot)
    $d = $StartDir
    while ($d) {
        if ((Test-Path (Join-Path $d 'pyproject.toml')) -and (Test-Path (Join-Path $d 'cli.py'))) {
            return (Resolve-Path -LiteralPath $d).Path
        }
        $next = Split-Path -Parent $d
        if (-not $next -or $next -eq $d) { break }
        $d = $next
    }
    return $null
}

function Get-GitPorcelainPath {
    param([Parameter(Mandatory)][string]$Line)
    $raw = $Line.TrimEnd()
    if ($raw -match ' -> ') {
        return ($raw -split ' -> ', 2)[-1].Trim()
    }
    if ($raw.Length -ge 4) {
        return $raw.Substring(3).Trim()
    }
    return $raw.Trim()
}

function Test-IsUnexpectedRepoRootEntry {
    param(
        [Parameter(Mandatory)][string]$Path,
        [string[]]$Allowlist = @(Get-HermesRepoRootAllowlist)
    )
    $norm = ($Path -replace '\\', '/')
    if ($norm -match '/') { return $false }
    return ($Allowlist -notcontains $norm)
}

function Get-QuickFixDestinationDir {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$FileName
    )
    $norm = $FileName -replace '\\', '/'
    if ($norm -match '\.(py|ps1|sh|bat)$') {
        return (Join-Path $RepoRoot 'output/research/scripts')
    }
    if ($norm -match '\.(xml|html|pdf|json|csv|xlsx|docx|pptx)$') {
        return (Join-Path $RepoRoot 'output/research/data')
    }
    if ($norm -match '\.(md|txt)$' -and $norm -match '(?i)bezwaar|rapport|concept|legal|avg') {
        return (Join-Path $RepoRoot 'output/legal')
    }
    return (Join-Path $RepoRoot 'output/research/reports')
}
