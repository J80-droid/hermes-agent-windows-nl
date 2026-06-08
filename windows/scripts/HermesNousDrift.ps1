# Shared tier-A drift helpers — dot-source from Test-NousTreeIdentical, catch-up, restore.
# SSOT policy: docs/NOUS_DRIFT_MAINTENANCE.md

# Always load in this script scope (parent may have functions without tier-path script vars).
. (Join-Path $PSScriptRoot 'HermesNousTierPaths.ps1')

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
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
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
        $ErrorActionPreference = $prevEap
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

function Invoke-HermesNousTierADriftCatchUp {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$UpstreamRef = 'upstream/main',
        [int]$TargetedMaxPaths = 15,
        [switch]$AllowTransitional,
        [switch]$SkipForkGate,
        [switch]$SkipBaseline,
        [switch]$Commit,
        [string]$CommitMessage = '',
        [switch]$QuietHeader
    )
    if (-not $QuietHeader) {
        Write-Host '=== Nous drift catch-up ===' -ForegroundColor Cyan
        Write-Host "Repo: $RepoRoot" -ForegroundColor DarkGray
        Write-Host 'Policy: docs/NOUS_DRIFT_MAINTENANCE.md' -ForegroundColor DarkGray
    }

    $report = Get-HermesNousTierADriftReport -RepoRoot $RepoRoot -UpstreamRef $UpstreamRef -AllowTransitional:$AllowTransitional
    foreach ($w in $report.ForkIntentional) {
        Write-Host "[WARN] fork-intentional (allowed): $w" -ForegroundColor Yellow
    }

    if ($report.MustUpstreamDrift.Count -eq 0) {
        Write-Host '[OK] Drift 0 - geen sync nodig.' -ForegroundColor Green
    } else {
        Write-Host ("[INFO] {0} tier-A pad(en) wijken af - sync starten" -f $report.MustUpstreamDrift.Count) -ForegroundColor Yellow
        if ($report.MustUpstreamDrift.Count -le $TargetedMaxPaths) {
            Invoke-HermesNousTierATargetedCheckout -RepoRoot $RepoRoot -Paths $report.MustUpstreamDrift -UpstreamRef $UpstreamRef
        } else {
            $restore = Join-Path $PSScriptRoot 'Invoke-RestoreNousTierA.ps1'
            & $restore -RepoRoot $RepoRoot -UpstreamRef $UpstreamRef
            if ($LASTEXITCODE -ne 0) { return $LASTEXITCODE }
        }

        $recheck = Get-HermesNousTierADriftReport -RepoRoot $RepoRoot -UpstreamRef $UpstreamRef -AllowTransitional:$AllowTransitional -SkipFetch
        if ($recheck.MustUpstreamDrift.Count -gt 0) {
            Write-Host "[FAIL] Drift na sync: $($recheck.MustUpstreamDrift.Count) pad(en)" -ForegroundColor Red
            foreach ($p in $recheck.MustUpstreamDrift) { Write-Host "  $p" -ForegroundColor Red }
            return 1
        }
        Write-Host '[OK] Drift 0 na sync.' -ForegroundColor Green
    }

    if (-not $SkipForkGate) {
        Write-Host '=== pytest fork gate ===' -ForegroundColor Cyan
        $forkGate = Join-Path $RepoRoot 'windows/tests/RUN_PYTEST_FORK_GATE.bat'
        cmd /c "`"$forkGate`""
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[FAIL] fork gate (exit $LASTEXITCODE)" -ForegroundColor Red
            return [int]$LASTEXITCODE
        }
        Write-Host '[OK] fork gate' -ForegroundColor Green
    }

    if (-not $SkipBaseline) {
        $export = Join-Path $PSScriptRoot 'Export-NousDriftBaseline.ps1'
        & $export -RepoRoot $RepoRoot -UpstreamRef $UpstreamRef
        if ($LASTEXITCODE -ne 0) { return [int]$LASTEXITCODE }
    }

    if ($Commit) {
        $status = @(git -C $RepoRoot status --porcelain 2>$null | Where-Object { $_.Trim() })
        if ($status.Count -eq 0) {
            Write-Host '[OK] Geen wijzigingen om te committen.' -ForegroundColor Green
        } else {
            git -C $RepoRoot add -A
            $msg = if ($CommitMessage) { $CommitMessage } else { 'chore(nous): sync tier-A to upstream/main (drift catch-up)' }
            git -C $RepoRoot commit -m $msg
            if ($LASTEXITCODE -ne 0) { return [int]$LASTEXITCODE }
            Write-Host "[OK] Commit: $msg" -ForegroundColor Green
        }
    }

    if (-not $QuietHeader) {
        Write-Host '=== Drift catch-up geslaagd ===' -ForegroundColor Green
    }
    return 0
}

function Invoke-HermesNousDriftGateWithCatchUp {
    <#
    .SYNOPSIS
      Detect tier-A drift vs upstream; optionally auto-run full catch-up chain.
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$UpstreamRef = 'upstream/main',
        [switch]$AllowTransitional,
        [switch]$SkipCatchUp,
        [switch]$Commit,
        [string]$CommitMessage = '',
        [switch]$Strict,
        [int]$TargetedMaxPaths = 15,
        [switch]$SkipForkGate,
        [switch]$SkipBaseline
    )

    $report = Get-HermesNousTierADriftReport -RepoRoot $RepoRoot -UpstreamRef $UpstreamRef -AllowTransitional:$AllowTransitional
    foreach ($w in $report.ForkIntentional) {
        Write-Host "[WARN] fork-intentional (allowed): $w" -ForegroundColor Yellow
    }

    if ($report.MustUpstreamDrift.Count -eq 0) {
        Write-Host '[OK] Tier A identical to upstream (within policy).' -ForegroundColor Green
        if (-not $SkipForkGate) {
            Write-Host '=== pytest fork gate (drift 0) ===' -ForegroundColor Cyan
            $forkGate = Join-Path $RepoRoot 'windows/tests/RUN_PYTEST_FORK_GATE.bat'
            cmd /c "`"$forkGate`""
            if ($LASTEXITCODE -ne 0) {
                Write-Host "[FAIL] fork gate (exit $LASTEXITCODE)" -ForegroundColor Red
                return [int]$LASTEXITCODE
            }
            Write-Host '[OK] fork gate' -ForegroundColor Green
        }
        return 0
    }

    Write-Host ("[FAIL] Tier A drift: {0} pad(en) vs {1}" -f $report.MustUpstreamDrift.Count, $UpstreamRef) -ForegroundColor Red
    foreach ($p in $report.MustUpstreamDrift) { Write-Host "  $p" -ForegroundColor Red }

    if ($SkipCatchUp) {
        Write-Host '[WARN] Auto catch-up overgeslagen (-SkipCatchUp).' -ForegroundColor Yellow
        Write-Host '[INFO] Draai: windows\UPDATE_HERMES.bat (auto catch-up)' -ForegroundColor DarkGray
        if ($Strict) { return 1 }
        return 0
    }

    Write-Host '[INFO] Auto catch-up starten (Invoke-HermesNousTierADriftCatchUp)...' -ForegroundColor Cyan
    $rc = Invoke-HermesNousTierADriftCatchUp `
        -RepoRoot $RepoRoot `
        -UpstreamRef $UpstreamRef `
        -TargetedMaxPaths $TargetedMaxPaths `
        -AllowTransitional:$AllowTransitional `
        -SkipForkGate:$SkipForkGate `
        -SkipBaseline:$SkipBaseline `
        -Commit:$Commit `
        -CommitMessage $CommitMessage `
        -QuietHeader
    if ($rc -ne 0) { return $rc }

    $final = Get-HermesNousTierADriftReport -RepoRoot $RepoRoot -UpstreamRef $UpstreamRef -AllowTransitional:$AllowTransitional -SkipFetch
    if ($final.MustUpstreamDrift.Count -gt 0) {
        Write-Host '[FAIL] Drift na auto catch-up.' -ForegroundColor Red
        return 1
    }
    Write-Host '[OK] Tier A drift gate + catch-up geslaagd.' -ForegroundColor Green
    return 0
}
