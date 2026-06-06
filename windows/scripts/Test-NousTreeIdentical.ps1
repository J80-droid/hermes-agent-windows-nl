# Fail if Tier A paths differ from upstream/main (Nous 100% intact gate).
param(
    [string]$RepoRoot = '',
    [string]$UpstreamRef = 'upstream/main',
    [switch]$AllowTransitional,
    [switch]$Quiet
)

$script:NousDriftQuiet = [bool]$Quiet

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

function Write-DriftLine {
    param([string]$Msg, [string]$Level = 'Info')
    if ($script:NousDriftQuiet) { return }
    switch ($Level) {
        'Error' { Write-Host $Msg -ForegroundColor Red }
        'Warn' { Write-Host $Msg -ForegroundColor Yellow }
        default { Write-Host $Msg }
    }
}

$repo = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { Get-HermesRepoRootLocal -Start $PSScriptRoot }
Push-Location $repo
try {
    $ErrorActionPreference = 'Continue'
    git fetch upstream 2>&1 | Out-Null
    $ErrorActionPreference = 'Stop'
    $failures = [System.Collections.Generic.List[string]]::new()
    $warnings = [System.Collections.Generic.List[string]]::new()

    $specs = Get-HermesTierAPathSpec
    $diffNames = @(git diff --name-only $UpstreamRef -- @specs 2>$null | Where-Object { $_.Trim() })
    foreach ($p in $diffNames) {
        if (Test-HermesPathTierAExcluded -Path $p) { continue }
        if (Test-HermesPathTierAForkIntentional -Path $p) {
            $warnings.Add("changed (fork-intentional): $p")
            continue
        }
        $isTrans = $false
        foreach ($t in $script:HermesNousTierATransitional) {
            if ($p -eq $t -or $p.StartsWith("$t/")) { $isTrans = $true; break }
        }
        if ($isTrans -and $AllowTransitional) {
            $warnings.Add("changed (transitional): $p")
        } else {
            $failures.Add("changed: $p")
        }
    }

    # Added paths vs upstream (working tree; deletions of fork-only files are OK)
    $added = @(git diff --name-only --diff-filter=A $UpstreamRef -- @specs 2>$null | Where-Object { $_.Trim() })
    foreach ($h in $added) {
        if (Test-HermesPathTierAExcluded -Path $h) { continue }
        if (Test-HermesPathTierAForkIntentional -Path $h) {
            $warnings.Add("added (fork-intentional): $h")
            continue
        }
        if (-not (Test-HermesPathUnderTierARoot -Path $h)) { continue }
        $isTrans = $false
        foreach ($t in $script:HermesNousTierATransitional) {
            if ($h -eq $t -or $h.StartsWith("$t/")) { $isTrans = $true; break }
        }
        if ($isTrans -and $AllowTransitional) {
            $warnings.Add("added (transitional): $h")
        } else {
            $failures.Add("added: $h")
        }
    }

    foreach ($w in $warnings) { Write-DriftLine -Msg "[WARN] $w" -Level 'Warn' }
    if ($failures.Count -eq 0) {
        Write-DriftLine -Msg '[OK] Tier A identical to upstream (within policy).' -Level 'Info'
        exit 0
    }
    Write-DriftLine -Msg "[FAIL] Tier A drift: $($failures.Count) issue(s)" -Level 'Error'
    foreach ($f in $failures) { Write-DriftLine -Msg "  $f" -Level 'Error' }
    Write-DriftLine -Msg 'Regenerate baseline: windows/scripts/Export-NousDriftBaseline.ps1' -Level 'Warn'
    exit 1
} finally {
    Pop-Location
}
