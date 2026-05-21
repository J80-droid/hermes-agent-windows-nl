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
    2) **start_hermes_split.bat** als aanwezig (Windows Terminal + log-paneel).
    3) **start_hermes.bat** (dunne shim naar windows\launch_hermes.bat).

    Zo kunnen IT-teams zonder scriptwijziging een eigen entrypoint afdwingen (GPO/User-env).
#>
function Get-HermesStartLauncherRelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )
    $trimmedRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

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

    $split = Join-Path $trimmedRoot 'start_hermes_split.bat'
    if (Test-Path -LiteralPath $split) {
        return 'start_hermes_split.bat'
    }
    return 'start_hermes.bat'
}
