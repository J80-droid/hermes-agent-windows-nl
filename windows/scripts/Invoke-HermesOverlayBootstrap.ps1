# Set PYTHONSTARTUP / PYTHONPATH so fork overlay hermes_cli modules load before cli.py.
param(
    [Parameter(Mandatory)]
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath $RepoRoot).Path
$startup = Join-Path $repo 'overlay\bootstrap_startup.py'
if (-not (Test-Path -LiteralPath $startup)) {
    Write-Warning "Overlay bootstrap ontbreekt: $startup"
    return
}
$env:HERMES_REPO_ROOT = $repo
$env:PYTHONPATH = $repo
if ($env:PYTHONPATH -notlike "*$repo*") {
    $env:PYTHONPATH = "$repo;$env:PYTHONPATH"
}
$env:PYTHONSTARTUP = $startup
$env:HERMES_OVERLAY_BOOTSTRAP = '1'
