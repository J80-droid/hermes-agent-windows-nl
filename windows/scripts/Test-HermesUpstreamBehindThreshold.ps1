# Lightweight upstream behind check — warn only, no merge. SSOT: docs/FORK_MERGE_POLICY.md
param(
    [string]$RepoRoot = '',
    [string]$UpstreamRef = 'upstream/main',
    [int]$Threshold = 0,
    [switch]$Quiet,
    [switch]$WarnOnly
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

if (-not $RepoRoot) {
    $d = $PSScriptRoot
    while ($d) {
        if ((Test-Path (Join-Path $d 'pyproject.toml')) -and (Test-Path (Join-Path $d 'cli.py'))) {
            $RepoRoot = (Resolve-Path -LiteralPath $d).Path
            break
        }
        $next = Split-Path -Parent $d
        if (-not $next -or $next -eq $d) { break }
        $d = $next
    }
}
if (-not $RepoRoot) {
    if (-not $Quiet) { Write-HermesWarn 'Repo root niet gevonden — upstream check overgeslagen.' }
    exit 0
}

$thresh = $Threshold
if ($thresh -le 0) {
    $thresh = 5
    if ($env:HERMES_UPSTREAM_BEHIND_WARN) {
        try { $thresh = [int]$env:HERMES_UPSTREAM_BEHIND_WARN } catch { $null = $_ }
    }
}

Push-Location $RepoRoot
try {
    $remotes = git remote 2>$null
    if ($remotes -notcontains 'upstream') {
        if (-not $Quiet) { Write-HermesInfo 'Geen upstream-remote — achterstand onbekend.' }
        exit 0
    }
    git fetch upstream --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        if (-not $Quiet) { Write-HermesWarn 'git fetch upstream mislukt — achterstand onbekend.' }
        exit 0
    }
    $lrRaw = git rev-list --left-right --count ('HEAD...' + $UpstreamRef) 2>$null
    if ($LASTEXITCODE -ne 0) {
        if (-not $Quiet) { Write-HermesWarn 'Kon fork vs upstream niet vergelijken.' }
        exit 0
    }
    $lr = if ($lrRaw) { ($lrRaw | Select-Object -First 1).ToString().Trim() -split '\s+' } else { @('0', '0') }
    if ($lr.Count -lt 2) { $lr = @('0', '0') }
    $behind = [int]$lr[1]

    if ($behind -lt $thresh) {
        if (-not $Quiet) {
            Write-HermesOk ("Upstream OK (behind={0}, drempel={1})." -f $behind, $thresh)
        }
        exit 0
    }

    if (-not $Quiet) {
        Write-Host ''
        Write-Host ('  [UPSTREAM] Fork loopt {0} commit(s) achter {1} (drempel {2}).' -f $behind, $UpstreamRef, $thresh) -ForegroundColor Yellow
        Write-Host '             Draai windows\UPDATE_HERMES.bat -Yes wanneer geen actieve chat/gateway.' -ForegroundColor Yellow
        Write-Host '             Zie docs\FORK_MERGE_POLICY.md — geen Taakplanner / geen auto-merge bij start.' -ForegroundColor DarkGray
        Write-Host ''
    }

    if ($WarnOnly) { exit 0 }
    exit 1
} finally {
    Pop-Location
}
