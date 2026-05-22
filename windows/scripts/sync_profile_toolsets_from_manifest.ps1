# Sync platform_toolsets.cli from docs/domain_toolsets.yaml naar Hermes-profielen + root.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [string]$Profile = '',
    [switch]$DryRun,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$py = $env:HERMES_PYTHON
if (-not $py) {
    $py = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
}
if (-not (Test-Path -LiteralPath $py)) {
    Write-Error "Python niet gevonden: $py"
}

$script = Join-Path $PSScriptRoot 'sync_profile_toolsets_from_manifest.py'
$argsList = @('--repo-root', $RepoRoot)
if ($HermesRoot) { $argsList += @('--hermes-root', $HermesRoot) }
if ($Profile) { $argsList += @('--profile', $Profile) }
if ($DryRun) { $argsList += '--dry-run' }
if ($Check) { $argsList += '--check' }

& $py $script @argsList
exit $LASTEXITCODE
