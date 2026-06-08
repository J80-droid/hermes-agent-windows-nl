# Migreer deprecated TERMINAL_CWD / MESSAGING_CWD uit profiel-.env naar config.yaml.
param(
    [string]$RepoRoot = '',
    [string]$ProfileName = 'core',
    [switch]$DryRun,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')
. (Join-Path $PSScriptRoot 'HermesHomeCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

$py = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
if (-not $py) {
    if (-not $Quiet) { Write-Host '[ERROR] Geen Python (hermes-env)' -ForegroundColor Red }
    exit 1
}

$runtimeRoot = Get-HermesRuntimeRoot
$profileHome = Join-Path (Join-Path $runtimeRoot 'profiles') $ProfileName
if (-not (Test-Path -LiteralPath (Join-Path $profileHome 'config.yaml'))) {
    if (-not $Quiet) {
        Write-Host "[WARN] Profiel $ProfileName niet gevonden onder $profileHome - overgeslagen" -ForegroundColor Yellow
    }
    exit 0
}

$env:HERMES_HOME = $profileHome
$script = Join-Path $RepoRoot 'scripts\repair_terminal_cwd.py'
$pyArgs = @($script, '--workspace', $RepoRoot)
if ($DryRun) { $pyArgs += '--dry-run' }

Push-Location $RepoRoot
try {
    if (-not $Quiet) {
        Write-Host "[INFO] TERMINAL_CWD-migratie voor profiel ${ProfileName} ($profileHome)" -ForegroundColor Cyan
    }
    & $py @pyArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
