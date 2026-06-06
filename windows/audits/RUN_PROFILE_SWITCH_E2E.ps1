. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

# E2E audit: institutional profile switch (Windows fork)
$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
Set-Location $repoRoot

function Find-Conda {
    foreach ($p in @(
        (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
        (Join-Path ${env:ProgramData} 'miniconda3\Scripts\conda.exe')
    )) {
        if ($p -and (Test-Path -LiteralPath $p)) { return $p }
    }
    throw 'conda.exe niet gevonden'
}

$conda = Find-Conda
$python = & $conda run -n hermes-env python -c "import sys; print(sys.executable)" 2>&1
if (Test-NativeCommandFailed) { throw "hermes-env python niet beschikbaar" }
$python = ($python | Select-Object -Last 1).Trim()

Write-Host '=== 1/5 verify_hermes_home ===' -ForegroundColor Cyan
& (Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/scripts/verify_hermes_home.ps1')
if (Test-NativeCommandFailed) { exit 1 }

Write-Host '=== 2/5 pytest profile switch subset ===' -ForegroundColor Cyan
Invoke-HermesAuditPytest -Python $python `
    tests/hermes_cli/test_apply_profile_override.py `
    tests/hermes_cli/test_profile_switch.py `
    tests/hermes_cli/test_relaunch.py::TestRelaunchChatAfterProfileSwitch `
    -q --tb=short
if (Test-NativeCommandFailed) { exit $LASTEXITCODE }

Write-Host '=== 3/5 SWITCH_PROFILE.bat (legal) ===' -ForegroundColor Cyan
$switchBat = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/SWITCH_PROFILE.bat'
& cmd /c "`"$switchBat`" legal"
if (Test-NativeCommandFailed) { exit $LASTEXITCODE }

$root = Join-Path $env:LOCALAPPDATA 'hermes'
if (-not (Test-Path -LiteralPath (Join-Path $root 'config.yaml'))) {
    $root = Join-Path $env:USERPROFILE '.hermes'
}
$activePath = Join-Path $root 'active_profile'
$active = (Get-Content -LiteralPath $activePath -Raw -Encoding UTF8).Trim()
if ($active -ne 'legal') {
    Write-Host ('[FAIL] ' + 'active_profile=' + $active + ' (verwacht legal)') -ForegroundColor Red
    exit 1
}
Write-Host '[OK]active_profile=legal' -ForegroundColor Green

Write-Host '=== 4/5 subprocess -p legal overrides stale HERMES_HOME ===' -ForegroundColor Cyan
$coreHome = Join-Path $root 'profiles\core'
$env:HERMES_HOME = $coreHome
& $python -m hermes_cli.main -p legal doctor --help 2>&1 | Out-Null
if (Test-NativeCommandFailed) {
    Write-Host '[FAIL] hermes -p legal doctor --help' -ForegroundColor Red
    exit 1
}
Write-Host '[OK] subprocess override smoke' -ForegroundColor Green

Write-Host '=== 5/5 cleanup sticky -> core ===' -ForegroundColor Cyan
& cmd /c "`"$switchBat`" core"
if (Test-NativeCommandFailed) { exit $LASTEXITCODE }

Write-Host '=== PROFILE SWITCH E2E: PASS ===' -ForegroundColor Green
exit 0
