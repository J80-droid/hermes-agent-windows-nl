#requires -Version 5.1
<#
.SYNOPSIS
  Bepaal of start_hermes.bat automatisch git pull + POST_GIT_PULL moet draaien.

.EXIT
  0 = up-to-date (geen pull nodig)
  1 = achter tracking branch (pull + sync aanbevolen)
  2 = overslaan (geen repo, merge bezig, vuile tree, fetch/count onbekend)
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$winDir = Split-Path -Parent $scriptDir

. (Join-Path $winDir 'HermesShellCommon.ps1')

if ($env:HERMES_SKIP_AUTO_PULL_ON_START -eq '1') {
    if (-not $Quiet) { Write-HermesInfo 'Auto-pull uit (HERMES_SKIP_AUTO_PULL_ON_START=1).' }
    exit 2
}

try {
    if (-not $RepoRoot) {
        $RepoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
    } else {
        $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
    }
} catch {
    if (-not $Quiet) { Write-HermesWarn ('RepoRoot ongeldig: ' + $_.Exception.Message) }
    exit 2
}

Push-Location -LiteralPath $RepoRoot
try {
    git rev-parse --is-inside-work-tree 2>$null | Out-Null
    if ((Test-NativeCommandFailed) -or ($LASTEXITCODE -ne 0)) {
        if (-not $Quiet) { Write-HermesWarn 'Geen git-checkout — auto-pull overgeslagen.' }
        exit 2
    }

    if (Test-Path -LiteralPath (Join-Path $RepoRoot '.git\MERGE_HEAD')) {
        if (-not $Quiet) { Write-HermesWarn 'Merge niet afgerond — auto-pull overgeslagen.' }
        exit 2
    }

    $dirty = git status --porcelain 2>$null
    if ($dirty -and ($dirty | Where-Object { $_.Trim() })) {
        if (-not $Quiet) { Write-HermesWarn 'Working tree niet schoon — auto-pull overgeslagen (gebruik --pull om te forceren).' }
        exit 2
    }

    $compareRef = $null
    $track = (git rev-parse --abbrev-ref '@{u}' 2>$null | Select-Object -First 1)
    if ($track) {
        $compareRef = $track.ToString().Trim()
    }
    if (-not $compareRef) {
        $compareRef = 'origin/main'
    }

    if ($env:HERMES_SKIP_FETCH_ON_START -ne '1') {
        $remote = if ($compareRef -match '^([^/]+)/') { $Matches[1] } else { 'origin' }
        git fetch $remote --quiet 2>$null
        $null = $LASTEXITCODE
    }

    $behindOut = git rev-list --count ('HEAD..' + $compareRef) 2>$null
    if ((Test-NativeCommandFailed) -or (-not $behindOut)) {
        if (-not $Quiet) { Write-HermesWarn 'Kon achterstand niet bepalen — auto-pull overgeslagen.' }
        exit 2
    }

    $behind = 0
    try {
        $behind = [int]($behindOut | Select-Object -First 1)
    } catch {
        if (-not $Quiet) { Write-HermesWarn 'Ongeldige rev-list output — auto-pull overgeslagen.' }
        exit 2
    }

    if ($behind -le 0) {
        if (-not $Quiet) { Write-HermesOk ('Repo up-to-date t.o.v. ' + $compareRef + ' — direct starten.') }
        exit 0
    }

    if (-not $Quiet) {
        Write-HermesInfo ($behind.ToString() + ' commit(s) achter ' + $compareRef + ' — pull + sync + relaunch.')
    }
    exit 1
} finally {
    Pop-Location
}
