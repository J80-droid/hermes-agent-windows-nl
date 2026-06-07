# Shared tier-A drift helpers — dot-source from Test-NousTreeIdentical, catch-up, restore.
# SSOT policy: docs/NOUS_DRIFT_MAINTENANCE.md

if (-not (Get-Command Test-HermesPathUnderTierARoot -ErrorAction SilentlyContinue)) {
    . (Join-Path $PSScriptRoot 'HermesNousTierPaths.ps1')
}

function Get-HermesRepoRootFromNousScripts {
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

function Invoke-HermesNousUpstreamFetch {
    param([string]$Remote = 'upstream')
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & git fetch $Remote 2>&1 | Out-Null
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Get-HermesNousTierADriftReport {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$UpstreamRef = 'upstream/main',
        [switch]$AllowTransitional,
        [switch]$SkipFetch
    )
    if (-not $SkipFetch) {
        Invoke-HermesNousUpstreamFetch | Out-Null
    }

    $failures = [System.Collections.Generic.List[string]]::new()
    $warnings = [System.Collections.Generic.List[string]]::new()
    $specs = Get-HermesTierAPathSpec

    Push-Location $RepoRoot
    try {
        $diffNames = @(git diff --name-only $UpstreamRef -- @specs 2>$null | Where-Object { $_.Trim() })
        foreach ($p in $diffNames) {
            if (Test-HermesPathTierAExcluded -Path $p) { continue }
            if (Test-HermesPathTierAForkIntentional -Path $p) {
                $warnings.Add($p)
                continue
            }
            $isTrans = $false
            foreach ($t in $script:HermesNousTierATransitional) {
                if ($p -eq $t -or $p.StartsWith("$t/")) { $isTrans = $true; break }
            }
            if ($isTrans -and $AllowTransitional) {
                $warnings.Add($p)
            } else {
                $failures.Add($p)
            }
        }

        $added = @(git diff --name-only --diff-filter=A $UpstreamRef -- @specs 2>$null | Where-Object { $_.Trim() })
        foreach ($h in $added) {
            if (Test-HermesPathTierAExcluded -Path $h) { continue }
            if (Test-HermesPathTierAForkIntentional -Path $h) {
                $warnings.Add($h)
                continue
            }
            if (-not (Test-HermesPathUnderTierARoot -Path $h)) { continue }
            $isTrans = $false
            foreach ($t in $script:HermesNousTierATransitional) {
                if ($h -eq $t -or $h.StartsWith("$t/")) { $isTrans = $true; break }
            }
            if ($isTrans -and $AllowTransitional) {
                $warnings.Add($h)
            } else {
                $failures.Add($h)
            }
        }
    } finally {
        Pop-Location
    }

    return [PSCustomObject]@{
        Failures           = @($failures)
        Warnings           = @($warnings)
        ForkIntentional    = @($warnings | Where-Object { Test-HermesPathTierAForkIntentional -Path $_ })
        MustUpstreamDrift  = @($failures)
    }
}

function Save-HermesNousTierAForkIntentionalFromHead {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$Ref = 'HEAD'
    )
    $saved = @{}
    Push-Location $RepoRoot
    try {
        foreach ($rel in $script:HermesNousTierAForkIntentional) {
            $norm = ($rel -replace '\\', '/')
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            $content = & git show "${Ref}:${norm}" 2>$null
            $ErrorActionPreference = $prevEap
            if ($LASTEXITCODE -eq 0 -and $null -ne $content) {
                $saved[$norm] = if ($content -is [array]) { $content -join "`n" } else { [string]$content }
            }
        }
    } finally {
        Pop-Location
    }
    return $saved
}

function Restore-HermesNousTierAForkIntentional {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][hashtable]$SavedFromHead
    )
    $common = Join-Path $PSScriptRoot '..\HermesShellCommon.ps1'
    if (Test-Path -LiteralPath $common) { . $common }
    foreach ($rel in $SavedFromHead.Keys) {
        $norm = ($rel -replace '\\', '/').TrimStart('./')
        $dest = if (Get-Command Join-HermesRepoPath -ErrorAction SilentlyContinue) {
            Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $norm
        } else {
            Join-Path $RepoRoot $norm
        }
        $parent = Split-Path -Parent $dest
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        $utf8 = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($dest, $SavedFromHead[$rel], $utf8)
        Write-Host "[OK] fork-intentional restored: $rel" -ForegroundColor DarkGreen
    }
}

function Invoke-HermesNousTierATargetedCheckout {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string[]]$Paths,
        [string]$UpstreamRef = 'upstream/main'
    )
    if ($Paths.Count -eq 0) { return }
    Push-Location $RepoRoot
    try {
        $saved = Save-HermesNousTierAForkIntentionalFromHead -RepoRoot $RepoRoot
        Write-Host ("[INFO] git checkout {0} -- {1} path(s)" -f $UpstreamRef, $Paths.Count) -ForegroundColor Cyan
        git checkout $UpstreamRef -- @Paths
        if ($LASTEXITCODE -ne 0) { throw "git checkout failed ($LASTEXITCODE)" }
        Restore-HermesNousTierAForkIntentional -RepoRoot $RepoRoot -SavedFromHead $saved
    } finally {
        Pop-Location
    }
}
