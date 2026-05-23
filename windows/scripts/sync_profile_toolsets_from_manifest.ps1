# Sync platform_toolsets.cli from docs/domain_toolsets.yaml naar Hermes-profielen + root.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [string]$Profile = '',
    [switch]$DryRun,
    [switch]$Check,
    [switch]$CreateMissing,
    [switch]$NoSoulInject,
    [switch]$SyncSoulSnippets,
    [switch]$ProvisionOnly,
    [string]$CloneFrom = ''
)

# BAT doorgeeft --flags als losse argumenten
if ($args -contains '--create-missing') { $CreateMissing = $true }
if ($args -contains '--no-soul-inject') { $NoSoulInject = $true }
if ($args -contains '--sync-soul-snippets') { $SyncSoulSnippets = $true }
if ($args -contains '--provision-only') { $ProvisionOnly = $true }
if (-not $CloneFrom) {
    $cfIdx = [array]::IndexOf($args, '--clone-from')
    if ($cfIdx -ge 0 -and $cfIdx + 1 -lt $args.Count) {
        $CloneFrom = $args[$cfIdx + 1]
    }
}

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
if ($CreateMissing) { $argsList += '--create-missing' }
if ($NoSoulInject) { $argsList += '--no-soul-inject' }
if ($SyncSoulSnippets) { $argsList += '--sync-soul-snippets' }
if ($ProvisionOnly) { $argsList += '--provision-only' }
if ($CloneFrom) { $argsList += @('--clone-from', $CloneFrom) }

& $py $script @argsList
exit $LASTEXITCODE
