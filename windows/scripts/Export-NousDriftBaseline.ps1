# Generate docs/NOUS_DRIFT_BASELINE.md — Tier A drift vs upstream/main.
param(
    [string]$RepoRoot = '',
    [string]$UpstreamRef = 'upstream/main',
    [string]$OutFile = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'HermesNousTierPaths.ps1')

function Invoke-HermesGitQuiet {
    param([Parameter(Mandatory)][string[]]$GitArgs)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & git @GitArgs 2>&1 | Out-Null
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Get-HermesGitLines {
    param([Parameter(Mandatory)][string[]]$GitArgs)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        return @(& git @GitArgs 2>$null | Where-Object { $_.Trim() })
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

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
$out = if ($OutFile) { $OutFile } else { Join-Path $repo 'docs/NOUS_DRIFT_BASELINE.md' }

Push-Location $repo
try {
    Invoke-HermesGitQuiet -GitArgs @('fetch', 'upstream') | Out-Null
    $changed = @(Get-HermesGitLines -GitArgs @('diff', '--name-only', $UpstreamRef))
    $tierAChanged = @()
    $tierBChanged = @()
    $transitionalHit = @()
    foreach ($p in $changed) {
        if (Test-HermesPathTierAExcluded -Path $p) {
            $tierBChanged += $p
            continue
        }
        if (Test-HermesPathUnderTierARoot -Path $p) {
            $tierAChanged += $p
            foreach ($t in $script:HermesNousTierATransitional) {
                if ($p -eq $t -or $p.StartsWith("$t/")) { $transitionalHit += $p; break }
            }
        } else {
            $tierBChanged += $p
        }
    }

    # Added in working tree vs upstream (Tier A)
    $specs = Get-HermesTierAPathSpec
    $extraInTierA = @(Get-HermesGitLines -GitArgs (@('diff', '--name-only', '--diff-filter=A', $UpstreamRef, '--') + @($specs)))
    $extraInTierA = @($extraInTierA | Where-Object {
            -not (Test-HermesPathTierAExcluded -Path $_) -and (Test-HermesPathUnderTierARoot -Path $_)
        })
    $tierAForkIntentional = @($tierAChanged | Where-Object { Test-HermesPathTierAForkIntentional -Path $_ })
    $tierAMustUpstream = @($tierAChanged | Where-Object { -not (Test-HermesPathTierAForkIntentional -Path $_) })

    $ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    $sb = [System.Text.StringBuilder]::new()
    [void]$sb.AppendLine("# NOUS drift baseline")
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine("Generated: **$ts**")
    [void]$sb.AppendLine("Compare: ``HEAD`` vs ``$UpstreamRef``")
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('## Summary')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine("| Metric | Count |")
    [void]$sb.AppendLine("|--------|------:|")
    [void]$sb.AppendLine("| All changed paths | $($changed.Count) |")
    [void]$sb.AppendLine("| Tier A changed (must -> upstream) | $($tierAMustUpstream.Count) |")
    [void]$sb.AppendLine("| Tier A changed (fork-intentional allowlist) | $($tierAForkIntentional.Count) |")
    [void]$sb.AppendLine("| Tier A extra files (fork-only in Nous dirs) | $($extraInTierA.Count) |")
    [void]$sb.AppendLine("| Tier B / excluded | $($tierBChanged.Count) |")
    [void]$sb.AppendLine("| Transitional (planned migration) | $($transitionalHit.Count) |")
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('## Tier A changed files (must -> upstream)')
    [void]$sb.AppendLine('')
    if ($tierAMustUpstream.Count -eq 0) {
        [void]$sb.AppendLine('_None._')
    } else {
        foreach ($p in ($tierAMustUpstream | Sort-Object)) {
            $mark = if ($transitionalHit -contains $p) { ' _(transitional)_' } else { '' }
            [void]$sb.AppendLine("- ``$p``$mark")
        }
    }
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('## Tier A changed files (fork-intentional allowlist)')
    [void]$sb.AppendLine('')
    if ($tierAForkIntentional.Count -eq 0) {
        [void]$sb.AppendLine('_None._')
    } else {
        foreach ($p in ($tierAForkIntentional | Sort-Object)) {
            [void]$sb.AppendLine("- ``$p`` _(fork-intentional; zie HermesNousTierPaths.ps1)_")
        }
    }
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('## Tier A extra files (not in upstream)')
    [void]$sb.AppendLine('')
    if ($extraInTierA.Count -eq 0) {
        [void]$sb.AppendLine('_None._')
    } else {
        foreach ($p in ($extraInTierA | Sort-Object)) {
            [void]$sb.AppendLine("- ``$p``")
        }
    }
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('## Regenerate')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('```powershell')
    [void]$sb.AppendLine('powershell -NoProfile -File windows/scripts/Export-NousDriftBaseline.ps1')
    [void]$sb.AppendLine('```')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('**Onderhoud (stabiel):** [NOUS_DRIFT_MAINTENANCE.md](NOUS_DRIFT_MAINTENANCE.md) — routine, scripts, taboe `SYNC_NOUS -Yes`.')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('**Catch-up:** `windows/SYNC_NOUS_DRIFT_CATCHUP.bat`')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('See [NOUS_OVERLAY_ARCHITECTURE.md](NOUS_OVERLAY_ARCHITECTURE.md).')

    $dir = Split-Path -Parent $out
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($out, $sb.ToString(), [System.Text.UTF8Encoding]::new($false))
    Write-Host "[OK] Wrote $out" -ForegroundColor Green
} finally {
    Pop-Location
}
