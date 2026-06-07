# Reset committed HEAD after production-gate tier-A postflight stages upstream files.
# Postflight uses `git checkout upstream/main -- <tier-A>` — staged only; `git restore .` is not enough.
param(
    [string]$RepoRoot = '',
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
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

function Test-HermesTierARepoPath {
    param([Parameter(Mandatory)][string]$Path)
    if (Test-HermesPathTierAExcluded -Path $Path) { return $false }
    return Test-HermesPathUnderTierARoot -Path $Path
}

$repo = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { Get-HermesRepoRootLocal -Start $PSScriptRoot }
Push-Location $repo
try {
    $staged = @(git diff --cached --name-only 2>$null | Where-Object { $_.Trim() })
    $tierAStaged = @($staged | Where-Object { Test-HermesTierARepoPath -Path $_ })

    if ($tierAStaged.Count -eq 0) {
        Write-Host '[OK] Geen staged tier-A wijzigingen — geen reset nodig.' -ForegroundColor Green
        exit 0
    }

    Write-Host ("[INFO] {0} staged tier-A pad(en) na postflight (bijv. {1})" -f $tierAStaged.Count, $tierAStaged[0]) -ForegroundColor Yellow
    if ($WhatIf) {
        Write-Host '[WHATIF] Zou uitvoeren: git reset --hard HEAD' -ForegroundColor Cyan
        exit 0
    }

    git reset --hard HEAD
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] git reset --hard HEAD (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host '[OK] Worktree teruggezet naar HEAD (tier-A postflight ongedaan).' -ForegroundColor Green
    exit 0
} finally {
    Pop-Location
}
