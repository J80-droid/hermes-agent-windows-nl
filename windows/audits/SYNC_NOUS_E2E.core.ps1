# E2E: overlay bootstrap + drift gate (transitional allowed) + manifest present.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$fail = 0

function Step-Ok([string]$Name) { Write-Host "[OK] $Name" -ForegroundColor Green }
function Step-Fail([string]$Name, [string]$Detail) {
    Write-Host "[FAIL] $Name - $Detail" -ForegroundColor Red
    $script:fail++
}

$manifest = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'overlay/manifest.yaml'
if (-not (Test-Path -LiteralPath $manifest)) { Step-Fail 'manifest' 'overlay/manifest.yaml' } else { Step-Ok 'overlay/manifest.yaml' }

$bootstrap = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'overlay/bootstrap.py'
if (-not (Test-Path -LiteralPath $bootstrap)) { Step-Fail 'bootstrap' 'overlay/bootstrap.py' } else { Step-Ok 'overlay/bootstrap.py' }

$py = $null
try { $py = Get-HermesPythonExe -RepoRoot $repoRoot } catch { $null = $_ }
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if ($py) {
    $code = 'from overlay.bootstrap import install; install(); import hermes_cli.institutional_render'
    & $py -c $code
    if ($LASTEXITCODE -eq 0) { Step-Ok 'python overlay bootstrap import' } else { Step-Fail 'bootstrap import' "exit $LASTEXITCODE" }
} else {
    Step-Fail 'python' 'geen interpreter'
}

$drift = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/scripts/Test-NousTreeIdentical.ps1'
& $drift -RepoRoot $repoRoot
if ($LASTEXITCODE -eq 0) { Step-Ok 'Test-NousTreeIdentical (strict green)' } else { Step-Fail 'Test-NousTreeIdentical' 'Tier A drift — zie docs/NOUS_DRIFT_BASELINE.md' }

if ($fail -gt 0) { exit 1 }
Write-Host '[OK] SYNC_NOUS E2E harness' -ForegroundColor Green
exit 0
