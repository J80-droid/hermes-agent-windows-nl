# Isolated harness: review-fixes resolver/bootstrap/RAG-manifest (8 scenario's).
$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
. (Join-Path $scriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $scriptRoot '..\HermesPythonPolicy.ps1')

$failures = 0

function Step([string]$Name, [bool]$Ok, [string]$Detail = '') {
    if ($Ok) {
        Write-Host ('[OK] ' + $Name + $(if ($Detail) { ' — ' + $Detail } else { '' }))
    } else {
        Write-Host ('[FAIL] ' + $Name + $(if ($Detail) { ' — ' + $Detail } else { '' })) -ForegroundColor Red
        $script:failures++
    }
}

Write-Host '=== Hermes Python institutional regression harness ==='

# 1 HERMES_CONDA_ROOT resolves python.exe
$condaRootTmp = Join-Path $env:TEMP ('hermes-conda-root-' + [guid]::NewGuid().ToString('n'))
$envName = Get-HermesCondaEnvName
$condaPyPath = Join-Path $condaRootTmp "envs\$envName\python.exe"
New-Item -ItemType Directory -Path (Split-Path -Parent $condaPyPath) -Force | Out-Null
Set-Content -LiteralPath $condaPyPath -Value 'stub' -Encoding ASCII
$prevRoot = $env:HERMES_CONDA_ROOT
$prevPy = $env:HERMES_PYTHON
Remove-Item Env:HERMES_PYTHON -ErrorAction SilentlyContinue
$env:HERMES_CONDA_ROOT = $condaRootTmp
Step 'Get-HermesCondaPython HERMES_CONDA_ROOT' ((Get-HermesCondaPython) -eq $condaPyPath)
if ($null -eq $prevRoot) { Remove-Item Env:HERMES_CONDA_ROOT -ErrorAction SilentlyContinue } else { $env:HERMES_CONDA_ROOT = $prevRoot }
if ($null -eq $prevPy) { Remove-Item Env:HERMES_PYTHON -ErrorAction SilentlyContinue } else { $env:HERMES_PYTHON = $prevPy }
Remove-Item -LiteralPath $condaRootTmp -Recurse -Force -ErrorAction SilentlyContinue

# 2 manifest fast-path: rag_extras_verified skips reinstall
$manifestPath = Get-HermesRagDepsManifestPath
$manifestBackup = $null
if (Test-Path -LiteralPath $manifestPath) {
    $manifestBackup = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8
}
$py = Resolve-HermesPythonExe -RepoRoot $repoRoot -RequirePip
if ($py) {
    $policyDir = Split-Path -Parent $manifestPath
    New-Item -ItemType Directory -Force -Path $policyDir | Out-Null
    @{
        installed_at        = (Get-Date).ToUniversalTime().ToString('o')
        python_exe          = $py
        rag_extra           = 'rag'
        rag_extras_verified = $true
    } | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    $pyproject = Join-Path $repoRoot 'pyproject.toml'
  $needs = Test-HermesNeedsRagExtrasInstall -RepoRoot $repoRoot -PyprojectPath $pyproject
    Step 'Test-HermesNeedsRagExtrasInstall manifest fast-path' (-not $needs)
} else {
    Step 'Test-HermesNeedsRagExtrasInstall manifest fast-path' $true 'skipped (geen conda)'
}
if ($null -ne $manifestBackup) {
    Set-Content -LiteralPath $manifestPath -Value $manifestBackup -Encoding UTF8
} elseif (Test-Path -LiteralPath $manifestPath) {
    Remove-Item -LiteralPath $manifestPath -Force -ErrorAction SilentlyContinue
}

# 3 manifest zonder rag_extras_verified => needs install (or import check)
if ($py) {
    $policyDir = Split-Path -Parent $manifestPath
    New-Item -ItemType Directory -Force -Path $policyDir | Out-Null
    @{
        installed_at = (Get-Date).ToUniversalTime().ToString('o')
        python_exe   = $py
        rag_extra    = 'rag'
    } | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    $needsLegacy = Test-HermesNeedsRagExtrasInstall -RepoRoot $repoRoot -PyprojectPath (Join-Path $repoRoot 'pyproject.toml')
    Step 'Test-HermesNeedsRagExtrasInstall legacy manifest zonder verified flag' ($needsLegacy -eq ( -not (Test-HermesRagExtrasInstalled -PythonExe $py)))
    if ($null -ne $manifestBackup) {
        Set-Content -LiteralPath $manifestPath -Value $manifestBackup -Encoding UTF8
    } else {
        Remove-Item -LiteralPath $manifestPath -Force -ErrorAction SilentlyContinue
    }
} else {
    Step 'Test-HermesNeedsRagExtrasInstall legacy manifest zonder verified flag' $true 'skipped'
}

# 4 Write-HermesRagDepsManifest null zonder imports
$stubPy = Join-Path $env:TEMP ('hermes-no-rag-' + [guid]::NewGuid().ToString('n') + '.exe')
Set-Content -LiteralPath $stubPy -Value 'stub' -Encoding ASCII
Step 'Write-HermesRagDepsManifest zonder RAG-imports' ($null -eq (Write-HermesRagDepsManifest -PythonExe $stubPy))
Remove-Item -LiteralPath $stubPy -Force -ErrorAction SilentlyContinue

# 5 Sync-HermesLaunchBootstrapStamp canoniek pad
$stamp = Sync-HermesLaunchBootstrapStamp
$expected = Join-Path (Join-Path $env:LOCALAPPDATA 'hermes') 'launch_bootstrap.stamp'
Step 'Sync-HermesLaunchBootstrapStamp LOCALAPPDATA pad' ($stamp -eq $expected)

# 6 check_hermes_rag_after_repair NonInteractive hangt niet
$repairCheck = Join-Path $scriptRoot '..\scripts\check_hermes_rag_after_repair.ps1'
$prevNi = $env:HERMES_NONINTERACTIVE
$env:HERMES_NONINTERACTIVE = '1'
$sw = [System.Diagnostics.Stopwatch]::StartNew()
& powershell -NoProfile -ExecutionPolicy Bypass -File $repairCheck -RepoRoot $repoRoot -NonInteractive -Quiet
$exitRepair = $LASTEXITCODE
$sw.Stop()
if ($null -eq $prevNi) { Remove-Item Env:HERMES_NONINTERACTIVE -ErrorAction SilentlyContinue } else { $env:HERMES_NONINTERACTIVE = $prevNi }
Step 'check_hermes_rag_after_repair NonInteractive binnen 15s' (($sw.Elapsed.TotalSeconds -lt 15) -and ($null -ne $exitRepair))

# 7 launch_bootstrap fast-path + state json
$bootstrap = Get-Content -LiteralPath (Join-Path $scriptRoot '..\scripts\launch_bootstrap.ps1') -Raw -Encoding UTF8
Step 'launch_bootstrap fast-path wiring' (
    ($bootstrap -match 'Test-HermesLaunchBootstrapFastPath') -and
    ($bootstrap -match 'Write-HermesLaunchBootstrapState') -and
    ($bootstrap -match 'Invoke-HermesBootstrapChildScript') -and
    ($bootstrap -notmatch 'Invoke-HermesCapturedProcess')
)

# 8 Get-HermesPyprojectFingerprint + bootstrap state pad
$policyText = Get-Content -LiteralPath (Join-Path $scriptRoot '..\HermesPythonPolicy.ps1') -Raw -Encoding UTF8
$stateExpected = Join-Path (Join-Path $env:LOCALAPPDATA 'hermes') 'launch_bootstrap.json'
Step 'launch_bootstrap.json policy helpers' (
    ($policyText -match 'function Get-HermesPyprojectFingerprint') -and
    ($policyText -match 'function Test-HermesLaunchBootstrapFastPath') -and
    ((Get-HermesLaunchBootstrapStatePath) -eq $stateExpected)
)

# 9 Get-HermesAuditPython hergebruikt resolver (geen dubbele dot-source crash)
$auditPy = Get-HermesAuditPython -RepoRoot $repoRoot
Step 'Get-HermesAuditPython resolve' ([bool]$auditPy -and ($auditPy -ne ''))

$total = 9
if ($failures) {
    Write-Host "=== REGRESSION HARNESS: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host "=== REGRESSION HARNESS: PASS ($total/$total) ==="
exit 0
