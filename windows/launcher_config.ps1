# =============================================================================
# Hermes — institutioneel: één plek voor welk repo-root .bat “Start” gebruikt.
# Wordt dot-gesourced door create_taskbar_shortcuts.ps1 en create_shortcut.ps1.
# =============================================================================

<#
.SYNOPSIS
    Bepaalt het relatieve pad (t.o.v. repo-root) van het start-launcher-batchbestand.

.DESCRIPTION
    Volgorde:
    1) Omgevingsvariabele **HERMES_START_BAT** (Process → User → Machine): alleen bestandsnaam,
       bijv. `org_start.bat`, moet op de repo-root bestaan. Geen paden met \ of / (geen submappen).
    2) **start_hermes.bat** (standaard: volledige launcher — SOUL, Docker, dashboard).
    2b) **start_hermes_minimal.bat** als `HERMES_START_BAT=start_hermes_minimal.bat` (snelle chat).
    3) **start_hermes_split.bat** alleen als `HERMES_START_SPLIT=1` (debug: chat + agent.log).

    Zo kunnen IT-teams zonder scriptwijziging een eigen entrypoint afdwingen (GPO/User-env).
#>
function Get-HermesStartLauncherRelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [ValidateSet('', 'minimal', 'full')]
        [string]$LaunchProfile = ''
    )
    $trimmedRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

    if ($LaunchProfile -eq 'full') {
        $fullBat = Join-Path $trimmedRoot 'start_hermes_full.bat'
        if (Test-Path -LiteralPath $fullBat) {
            return 'start_hermes_full.bat'
        }
    }
    if ($LaunchProfile -eq 'minimal') {
        $minBat = Join-Path $trimmedRoot 'start_hermes_minimal.bat'
        if (Test-Path -LiteralPath $minBat) {
            return 'start_hermes_minimal.bat'
        }
    }

    foreach ($scope in @('Process', 'User', 'Machine')) {
        $raw = [Environment]::GetEnvironmentVariable('HERMES_START_BAT', $scope)
        if ([string]::IsNullOrWhiteSpace($raw)) { continue }
        $leaf = $raw.Trim().TrimStart('\', '/')
        if ($leaf -match '[\\/]') { continue }
        if ($leaf -notmatch '\.(bat|cmd)$') { continue }
        $full = Join-Path $trimmedRoot $leaf
        if (Test-Path -LiteralPath $full) {
            return $leaf
        }
    }

    $wantSplit = $false
    if ($env:HERMES_START_SPLIT -eq '1') { $wantSplit = $true }
    $split = Join-Path $trimmedRoot 'start_hermes_split.bat'
    if ($wantSplit -and (Test-Path -LiteralPath $split)) {
        return 'start_hermes_split.bat'
    }
    return 'start_hermes.bat'
}
