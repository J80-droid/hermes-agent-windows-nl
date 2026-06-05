# Hermes split-home E2E — implementatie (dot-source alleen hier).
param(
    [string]$RepoRoot = '',
    [switch]$StrictDrift,
    [switch]$SkipPytest
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

function Add-StepResult {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    $steps.Add([pscustomobject]@{ Step = $Name; Ok = $Ok; Detail = $Detail })
    $suffix = if ($Detail) { ' — ' + $Detail } else { '' }
    if ($Ok) {
        Write-Host ('[OK] ' + $Name + $suffix) -ForegroundColor Green
    } else {
        Write-Host ('[FAIL] ' + $Name + $suffix) -ForegroundColor Red
        $script:failures++
    }
}

Write-Host '=== HermesHome E2E ===' -ForegroundColor Cyan
Write-Host "[INFO] Repo: $RepoRoot" -ForegroundColor Cyan

$repoArtifacts = @(
    'windows/scripts/HermesHomeCommon.ps1',
    'windows/apply_hermes_home_migration.ps1',
    'windows/APPLY_HERMES_HOME_MIGRATION.bat',
    'windows/DEPRECATE_LEGACY_CONFIG.bat',
    'windows/APPLY_AUXILIARY_HYBRID_PRESET.bat',
    'windows/scripts/merge_legacy_providers_config.py',
    'windows/scripts/strip_profile_global_config_blocks.py',
    'docs/templates/PROVIDERS_VENICE.yaml',
    'docs/HERMES_HOME_WINDOWS.md',
    'docs/templates/SOUL_SHARED_CONFIG_GOVERNANCE.md',
    'docs/templates/AUXILIARY_HYBRID_OLLAMA.yaml'
)
$missingRepo = @($repoArtifacts | Where-Object {
    -not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $_))
})
$repoDetail = if ($missingRepo.Count) { ($missingRepo -join ', ') } else { "$($repoArtifacts.Count) bestanden" }
Add-StepResult '1/16 Repo split-home artefacten' ($missingRepo.Count -eq 0) $repoDetail

if (-not $SkipPytest) {
    $conda = Join-Path $env:USERPROFILE 'miniconda3/Scripts/conda.exe'
    if (Test-Path -LiteralPath $conda) {
        Push-Location $RepoRoot
        $savedHermesHome = $env:HERMES_HOME
        Remove-Item Env:HERMES_HOME -ErrorAction SilentlyContinue
        try {
            & $conda run -n hermes-env --no-capture-output python -m pytest `
                tests/hermes_cli/test_doctor.py::TestWindowsSplitHomeCheck `
                tests/hermes_cli/test_profile_model_inheritance.py `
                tests/hermes_cli/test_merge_legacy_providers_config.py `
                tests/test_hermes_constants.py `
                tests/hermes_cli/test_config.py::TestGetConfigValue `
                tests/hermes_cli/test_apply_profile_override.py `
                -q --tb=line
        } finally {
            if ($savedHermesHome) { $env:HERMES_HOME = $savedHermesHome } else { Remove-Item Env:HERMES_HOME -ErrorAction SilentlyContinue }
            Pop-Location
        }
        Add-StepResult '2/16 pytest split-home subset' ($LASTEXITCODE -eq 0)
    } else {
        Write-Host '[SKIP] 2/16 pytest split-home — conda niet gevonden' -ForegroundColor Yellow
    }
} else {
    Write-Host '[SKIP] 2/16 pytest split-home (-SkipPytest)' -ForegroundColor Yellow
}

$rootA = Get-HermesRuntimeRoot
. (Join-Path $windowsRoot (Join-Path 'scripts' 'HermesBackupCommon.ps1'))
$rootB = Get-HermesRuntimeRoot
Add-StepResult '3/16 Get-HermesRuntimeRoot consistent' ($rootA -eq $rootB) ($rootA + ' vs ' + $rootB)

$legacyCfg = Get-HermesLegacyConfigPath
$legacyRoot = Get-HermesLegacyRoot
$legacyDetail = if (Test-Path -LiteralPath $legacyCfg) { $legacyCfg } else { 'deprecated-only OK' }
Add-StepResult '4/16 Geen actieve legacy config.yaml' (-not (Test-Path -LiteralPath $legacyCfg)) $legacyDetail

$readme = Join-Path $legacyRoot 'CONFIG_README.txt'
$deprecated = @(Get-ChildItem -LiteralPath $legacyRoot -Filter 'config.yaml.deprecated-*' -File -ErrorAction SilentlyContinue)
$legacyOk = (Test-Path -LiteralPath $readme) -or ($deprecated.Count -gt 0) -or (-not (Test-Path -LiteralPath $legacyRoot))
$legacyHubDetail = if (Test-Path -LiteralPath $readme) {
    'CONFIG_README.txt'
} elseif ($deprecated.Count) {
    $deprecated[0].Name
} else {
    'legacy hub ontbreekt'
}
Add-StepResult '5/16 Legacy hub README of archive' $legacyOk $legacyHubDetail

$inventory = Join-HermesRepoPath -RepoRoot $windowsRoot -RelativePath 'scripts/inventory_hermes_home.ps1'
& $inventory -Quiet
Add-StepResult '6/16 inventory_hermes_home -Quiet' ($LASTEXITCODE -eq 0)

Initialize-UserHermesHomeRoot -FixUserEnv -Quiet | Out-Null
$env:HERMES_HOME = (Get-HermesRuntimeRoot).TrimEnd('\')

$verifyHome = Join-HermesRepoPath -RepoRoot $windowsRoot -RelativePath 'scripts/verify_hermes_home.ps1'
& $verifyHome -StrictDrift:$StrictDrift
Add-StepResult '7/16 verify_hermes_home' ($LASTEXITCODE -eq 0)

$verifyDrift = Join-HermesRepoPath -RepoRoot $windowsRoot -RelativePath 'scripts/verify_hermes_config_drift.ps1'
& $verifyDrift -Strict:$StrictDrift
Add-StepResult '8/16 verify_hermes_config_drift' ($LASTEXITCODE -eq 0)

$expected = (Get-HermesRuntimeRoot).TrimEnd('\')
Initialize-UserHermesHomeRoot -FixUserEnv -Quiet | Out-Null
$procHome = if ($env:HERMES_HOME) { $env:HERMES_HOME.TrimEnd('\') } else { '' }
Add-StepResult '9/16 Initialize-UserHermesHomeRoot proces-env' ($procHome -eq $expected) $procHome

$userHome = [Environment]::GetEnvironmentVariable('HERMES_HOME', 'User')
$userOk = $true
$userDetail = if ($userHome) { $userHome } else { '(niet gezet)' }
if ($userHome) {
    $userPath = $userHome.TrimEnd('\')
    if ($userPath -match '\\profiles\\[^\\]+$') {
        $userOk = $false
        $userDetail = 'User HERMES_HOME wijst naar profielsubmap'
    } elseif ($userPath -ne $expected) {
        $userOk = $false
    }
}
Add-StepResult '10/16 User HERMES_HOME = runtime root' $userOk $userDetail

$gwOk = Test-HermesGatewayHomeAlignment -Quiet
Add-StepResult '11/16 Test-HermesGatewayHomeAlignment' $gwOk 'REPAIR_GATEWAY_HOME.bat'

$profileBlockIssues = Test-HermesProfileGlobalConfigBlocks -Quiet
$profileBlockDetail = if ($profileBlockIssues.Count) { $profileBlockIssues -join '; ' } else { 'OK' }
Add-StepResult '12/16 Geen profile auxiliary/providers blocks' ($profileBlockIssues.Count -eq 0) $profileBlockDetail

$veniceOk = Test-HermesVeniceProviderConfigured -Quiet
$veniceDetail = if ($veniceOk) { 'providers.venice present or not required' } else { 'restore merge_legacy_providers_config.py' }
Add-StepResult '13/16 Venice provider in runtime config' $veniceOk $veniceDetail

$legacyEnv = Join-Path (Get-HermesLegacyRoot) '.env'
$runtimeEnv = Join-Path (Get-HermesRuntimeRoot) '.env'
$veniceEnvOk = $true
$veniceEnvDetail = 'n/a'
if ((Test-Path -LiteralPath $legacyEnv) -and (Select-String -Path $legacyEnv -Pattern '^\s*VENICE_API_KEY\s*=\s*\S+' -Quiet)) {
    $veniceEnvOk = (Test-Path -LiteralPath $runtimeEnv) -and (
        Select-String -Path $runtimeEnv -Pattern '^\s*VENICE_API_KEY\s*=\s*\S+' -Quiet
    )
    $veniceEnvDetail = if ($veniceEnvOk) { 'VENICE_API_KEY in runtime .env' } else { 'run SYNC_HERMES_API_ENV.bat' }
}
Add-StepResult '14/16 VENICE_API_KEY synced to runtime' $veniceEnvOk $veniceEnvDetail

$jatevoOk = Test-HermesJatevoProviderConfigured -Quiet
$jatevoDetail = if ($jatevoOk) { 'providers.jatevo present or not required' } else { 'restore merge_legacy_providers_config.py' }
Add-StepResult '15/16 Jatevo provider in runtime config' $jatevoOk $jatevoDetail

$jatevoEnvOk = $true
$jatevoEnvDetail = 'n/a'
if ((Test-Path -LiteralPath $legacyEnv) -and (Select-String -Path $legacyEnv -Pattern '^\s*JATEVO_API_KEY\s*=\s*\S+' -Quiet)) {
    $jatevoEnvOk = (Test-Path -LiteralPath $runtimeEnv) -and (
        Select-String -Path $runtimeEnv -Pattern '^\s*JATEVO_API_KEY\s*=\s*\S+' -Quiet
    )
    $jatevoEnvDetail = if ($jatevoEnvOk) { 'JATEVO_API_KEY in runtime .env' } else { 'run SYNC_HERMES_API_ENV.bat' }
}
Add-StepResult '16/16 JATEVO_API_KEY synced to runtime' $jatevoEnvOk $jatevoEnvDetail

$runtimeCfg = Get-HermesCanonicalConfigPath
if (Test-Path -LiteralPath $runtimeCfg) {
    $conda = Join-Path $env:USERPROFILE 'miniconda3/Scripts/conda.exe'
    if (Test-Path -LiteralPath $conda) {
        $overlayCli = Join-Path $RepoRoot 'scripts/run_hermes_cli_with_overlay.py'
        $visionOut = & $conda run -n hermes-env --cwd $RepoRoot --no-capture-output python $overlayCli config get auxiliary.vision.provider 2>&1
        if ($LASTEXITCODE -eq 0) {
            $val = ($visionOut | Select-Object -Last 1).ToString().Trim().ToLower()
            Add-StepResult 'auxiliary.vision.provider=gemini' ($val -eq 'gemini') $val
            $coreProf = Join-Path (Get-HermesRuntimeRoot) 'profiles\core\config.yaml'
            if (Test-Path -LiteralPath $coreProf) {
                $prevHome = $env:HERMES_HOME
                $env:HERMES_HOME = (Split-Path -Parent $coreProf)
                $compOut = & $conda run -n hermes-env --cwd $RepoRoot --no-capture-output python $overlayCli config get auxiliary.compression.provider 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $compVal = ($compOut | Select-Object -Last 1).ToString().Trim().ToLower()
                    Add-StepResult 'profile core inherits auxiliary.compression=custom' ($compVal -eq 'custom') $compVal
                }
                if ($prevHome) { $env:HERMES_HOME = $prevHome } else { Remove-Item Env:HERMES_HOME -ErrorAction SilentlyContinue }
                Initialize-UserHermesHomeRoot -FixUserEnv -Quiet | Out-Null
            }
        } else {
            Add-StepResult 'auxiliary.vision.provider=gemini' $false 'CLI exit non-zero'
        }
    } else {
        Write-Host '[SKIP] auxiliary.vision.provider — conda niet gevonden' -ForegroundColor Yellow
    }
}

$reportPath = Join-Path $scriptRoot ("HERMES_HOME_E2E_REPORT_$stamp.md")
$lines = @(
    '# Hermes split-home E2E report',
    '',
    "- Timestamp: $stamp",
    "- Repo: $RepoRoot",
    "- Runtime: $(Get-HermesRuntimeRoot)",
    '',
    '| Step | OK | Detail |',
    '| --- | --- | --- |'
)
foreach ($s in $steps) {
    $okMark = if ($s.Ok) { 'yes' } else { '**no**' }
    $detail = if ($s.Detail) { $s.Detail -replace '\|', '/' } else { '' }
    $lines += "| $($s.Step) | $okMark | $detail |"
}
$lines += ''
$lines += "Failures: $failures"
Set-Content -LiteralPath $reportPath -Value ($lines -join "`n") -Encoding UTF8
Write-Host "[INFO] Rapport: $reportPath" -ForegroundColor Cyan

Write-Host ''
if ($failures -gt 0) {
    Write-Host ("HermesHome E2E: $failures stap(pen) gefaald") -ForegroundColor Red
    exit 1
}
Write-Host 'HermesHome E2E: alles geslaagd' -ForegroundColor Green
exit 0
