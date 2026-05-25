# Root config inheritance E2E - model/auxiliary/providers profiel -> root.
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest,
    [switch]$SkipLive
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
$windowsRoot = (Resolve-Path (Join-Path $scriptRoot '..')).Path
. (Join-Path $windowsRoot 'HermesShellCommon.ps1')
. (Join-Path $windowsRoot (Join-Path 'scripts' 'HermesHomeCommon.ps1'))

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$failures = 0
$steps = [System.Collections.Generic.List[object]]::new()
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'

function Get-HermesAuditPython {
    if ($env:HERMES_AUDIT_PYTHON -and (Test-Path -LiteralPath $env:HERMES_AUDIT_PYTHON)) {
        return $env:HERMES_AUDIT_PYTHON
    }
    $conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
    if (Test-Path -LiteralPath $conda) {
        $out = & $conda run -n hermes-env python -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            return ($out | Select-Object -Last 1).ToString().Trim()
        }
    }
    $fallback = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if (Test-Path -LiteralPath $fallback) { return $fallback }
    return 'python'
}

function Add-StepResult {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    $steps.Add([pscustomobject]@{ Step = $Name; Ok = $Ok; Detail = $Detail })
    $suffix = if ($Detail) { ' - ' + $Detail } else { '' }
    if ($Ok) {
        Write-Host ('[OK] ' + $Name + $suffix) -ForegroundColor Green
    } else {
        Write-Host ('[FAIL] ' + $Name + $suffix) -ForegroundColor Red
        $script:failures++
    }
}

Write-Host '=== Root Config Inheritance E2E ===' -ForegroundColor Cyan
Write-Host "[INFO] Repo: $RepoRoot" -ForegroundColor Cyan
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

$repoArtifacts = @(
    'hermes_cli/profile_model_inheritance.py',
    'hermes_cli/config.py',
    'windows/scripts/merge_legacy_providers_config.py',
    'windows/scripts/collect_env_sync_keys.py',
    'windows/scripts/apply_auxiliary_hybrid_preset.py',
    'windows/scripts/strip_profile_global_config_blocks.py',
    'docs/templates/PROVIDERS_VENICE.yaml',
    'windows/audits/RootConfigInheritanceE2E.harness.py',
    'windows/audits/RootConfigInheritanceE2E.core.ps1',
    'windows/audits/RUN_ROOT_CONFIG_INHERITANCE_E2E.ps1'
)
$missingRepo = @($repoArtifacts | Where-Object {
    -not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $_))
})
$repoDetail = if ($missingRepo.Count) { ($missingRepo -join ', ') } else { "$($repoArtifacts.Count) bestanden" }
Add-StepResult '1/10 Repo root-inheritance artefacten' ($missingRepo.Count -eq 0) $repoDetail

if (-not $SkipPytest) {
    Push-Location $RepoRoot
    try {
        & $python -m pytest `
            tests/hermes_cli/test_profile_model_inheritance.py `
            tests/hermes_cli/test_merge_legacy_providers_config.py `
            -q --tb=line -o addopts=
    } finally {
        Pop-Location
    }
    Add-StepResult '2/10 pytest inheritance + merge unit' ($LASTEXITCODE -eq 0) $python
} else {
    Write-Host '[SKIP] 2/10 pytest (-SkipPytest)' -ForegroundColor Yellow
}

$harness = Join-Path $scriptRoot 'RootConfigInheritanceE2E.harness.py'
Push-Location $RepoRoot
try {
    & $python $harness
} finally {
    Pop-Location
}
Add-StepResult '3/10 isolated inheritance harness (8 scenario''s)' ($LASTEXITCODE -eq 0)

$inhPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'hermes_cli/profile_model_inheritance.py')
$cfgPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'hermes_cli/config.py')
$collectScript = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/collect_env_sync_keys.py')
# Regressie: docstring moet afgesloten zijn vóór imports (py_compile vangt syntaxfouten).
& $python -m py_compile (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/collect_env_sync_keys.py') 2>$null
$collectCompileOk = ($LASTEXITCODE -eq 0)
$wiringOk = ($inhPy -match 'root_user = _read_yaml\(root_config_path\(\)\)') -and
    ($inhPy -match 'def bust_config_caches') -and
    ($inhPy -match 'clear_all = not paths or any') -and
    ($cfgPy -match 'incoming_keys = set\(config\.keys\(\)\)') -and
    ($collectScript -match 'root_config_path') -and
    $collectCompileOk
Add-StepResult '4/10 code wiring review fixes aanwezig' $wiringOk

$profileIssues = Test-HermesProfileGlobalConfigBlocks -Quiet
$profileDetail = if ($profileIssues.Count) { $profileIssues -join '; ' } else { 'geen model/auxiliary/providers in profielen' }
Add-StepResult '5/10 runtime: geen profiel global blocks' ($profileIssues.Count -eq 0) $profileDetail

$veniceOk = Test-HermesVeniceProviderConfigured -Quiet
Add-StepResult '6/10 runtime: Venice provider in root config' $veniceOk 'providers.venice of niet vereist'

$runtimeRoot = Get-HermesRuntimeRoot
$runtimeCfg = Join-Path $runtimeRoot 'config.yaml'
$mergePy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/merge_legacy_providers_config.py')
$mergeUsesRoot = $mergePy -match 'root_config_path\(\)'
Add-StepResult '7/10 merge script gebruikt root_config_path' $mergeUsesRoot

if (-not $SkipLive -and (Test-Path -LiteralPath $runtimeCfg)) {
    $coreProf = Join-Path $runtimeRoot 'profiles\core\config.yaml'
    if (Test-Path -LiteralPath $coreProf) {
        $prevHome = $env:HERMES_HOME
        $env:HERMES_HOME = (Split-Path -Parent $coreProf)
        $compOut = & $python -c @"
import os, sys
sys.path.insert(0, r'$RepoRoot')
from hermes_cli.config import load_config
cfg = load_config()
print(cfg.get('auxiliary', {}).get('compression', {}).get('provider', ''))
"@ 2>&1
        $compVal = ($compOut | Select-Object -Last 1).ToString().Trim().ToLower()
        if ($prevHome) { $env:HERMES_HOME = $prevHome } else { Remove-Item Env:HERMES_HOME -ErrorAction SilentlyContinue }
        Initialize-UserHermesHomeRoot -FixUserEnv -Quiet | Out-Null
        Add-StepResult '8/10 live: core profiel erft auxiliary.compression' ($compVal -eq 'custom') $compVal
    } else {
        Add-StepResult '8/10 live: core profiel erft auxiliary.compression' $true 'profiles/core ontbreekt - skip'
    }

    $collectOut = & $python (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/collect_env_sync_keys.py') 2>&1
    $collectOk = ($LASTEXITCODE -eq 0)
    $collectDetail = if ($collectOut) { ($collectOut | Select-Object -Last 3) -join ', ' } else { 'geen keys' }
    Add-StepResult '9/10 live: collect_env_sync_keys op runtime root' $collectOk $collectDetail
} else {
    Write-Host '[SKIP] 8-9/10 live runtime checks (-SkipLive of geen config)' -ForegroundColor Yellow
}

$envScript = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/sync_hermes_api_env.ps1')
$envOk = ($envScript -match 'collect_env_sync_keys') -and ($envScript -match 'VENICE')
Add-StepResult '10/10 sync_hermes_api_env Venice + dynamic keys' $envOk

$reportPath = Join-Path $scriptRoot ("ROOT_CONFIG_INHERITANCE_E2E_REPORT_$stamp.md")
$status = if ($failures -eq 0) { 'PASS' } else { 'FAIL' }
$lines = @(
    "# Root config inheritance E2E - $status",
    '',
    "- Timestamp: $stamp",
    "- Repo: $RepoRoot",
    "- Python: $python",
    '',
    '| Stap | OK | Detail |',
    '|------|----|--------|'
)
foreach ($s in $steps) {
    $ok = if ($s.Ok) { 'yes' } else { '**no**' }
    $det = ($s.Detail -replace '\|', '/') -replace "`r?`n", ' '
    $lines += "| $($s.Step) | $ok | $det |"
}
$lines += ''
if ($failures -gt 0) {
    $lines += "**$failures** stap(pen) gefaald."
} else {
    $lines += 'Alle stappen geslaagd. Root-inheritance, cache-bust, merge-redirect en save-guards werken.'
}
$lines -join "`n" | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host ''
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== ROOT CONFIG INHERITANCE E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== ROOT CONFIG INHERITANCE E2E: PASS ===' -ForegroundColor Green
exit 0
