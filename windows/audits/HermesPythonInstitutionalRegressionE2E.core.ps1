# Review-fixes E2E: bootstrap stamp, RAG-manifest fast-path, non-interactive REPAIR, HERMES_CONDA_ROOT.
# Launcher: RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E.ps1
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest
)

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$failures = 0
$steps = [System.Collections.Generic.List[object]]::new()

function Add-StepResult {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    $steps.Add([pscustomobject]@{ Step = $Name; Ok = $Ok; Detail = $Detail })
    if ($Ok) {
        Write-Host ('[OK] ' + $Name + $(if ($Detail) { ' - ' + $Detail } else { '' })) -ForegroundColor Green
    } else {
        Write-Host ('[FAIL] ' + $Name + $(if ($Detail) { ' - ' + $Detail } else { '' })) -ForegroundColor Red
        $script:failures++
    }
}

function Invoke-AuditCommand {
    param(
        [Parameter(Mandatory)][string]$Exe,
        [string[]]$ArgumentList = @()
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $out = & $Exe @ArgumentList 2>&1
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEap
    foreach ($line in @($out)) {
        if ($null -ne $line -and "$line".Trim()) {
            Write-Host $line
        }
    }
    return $ok
}

Write-Host '=== Hermes Python institutional regression E2E ===' -ForegroundColor Cyan
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$python = Get-HermesAuditPython -RepoRoot $RepoRoot

# --- 1 Review artefacten ---
$repoFiles = @(
    'windows/scripts/check_hermes_rag_after_repair.ps1',
    'windows/scripts/launch_bootstrap.ps1',
    'windows/HermesPythonPolicy.ps1',
    'tests/windows/test_hermes_python_institutional.py'
)
$artOk = $true
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $artOk = $false
        break
    }
}
Add-StepResult -Name '1/8 review-fix repo artefacten' -Ok $artOk

# --- 2 Policy review helpers ---
$policyPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/HermesPythonPolicy.ps1')
$policyOk = ($policyPy -match 'rag_extras_verified') -and
    ($policyPy -match 'function Test-HermesNeedsRagExtrasInstall') -and
    ($policyPy -match 'HERMES_CONDA_ROOT') -and
    ($policyPy -match 'Resolve-HermesPythonExe -RepoRoot \$RepoRoot -RequirePip')
Add-StepResult -Name '2/8 policy review helpers (manifest fast-path + CONDA_ROOT)' -Ok $policyOk

# --- 3 Bootstrap stamp guard ---
$bootstrap = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/launch_bootstrap.ps1')
$bootstrapOk = ($bootstrap -match 'Test-HermesNeedsRagExtrasInstall') -and
    ($bootstrap -match '\$ragOk') -and
    ($bootstrap -match 'Sync-HermesLaunchBootstrapStamp')
Add-StepResult -Name '3/8 launch_bootstrap stamp + needs-RAG wiring' -Ok $bootstrapOk

# --- 4 REPAIR non-interactive ---
$repairCheck = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/check_hermes_rag_after_repair.ps1')
$repairOk = ($repairCheck -match '\[switch\]\$NonInteractive') -and
    ($repairCheck -match 'HERMES_NONINTERACTIVE') -and
    ($repairCheck -match 'IsInputRedirected')
$repairBat = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/REPAIR_PYTHON.bat')
$repairOk = $repairOk -and ($repairBat -match 'check_hermes_rag_after_repair')
Add-StepResult -Name '4/8 REPAIR RAG-check non-interactive wiring' -Ok $repairOk

# --- 5 Isolated harness (8 scenario''s) ---
$harness = Join-Path $scriptRoot 'HermesPythonInstitutionalRegressionE2E.harness.ps1'
$harnessOk = Invoke-AuditCommand -Exe 'powershell' -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $harness
)
Add-StepResult -Name '5/8 isolated regression harness (8 scenario''s)' -Ok $harnessOk

# --- 6 pytest subset ---
if ($SkipPytest) {
    Add-StepResult -Name '6/8 pytest institutional subset' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $pytestOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/windows/test_hermes_python_institutional.py'),
        '-q', '--tb=short', '-o', 'addopts='
    )
    Add-StepResult -Name '6/8 pytest institutional subset' -Ok $pytestOk -Detail $python
}

# --- 7 setup stamp canoniek pad ---
$setupPs1 = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/windows/setup_hermes_windows.ps1')
$setupOk = ($setupPs1 -match 'Sync-HermesLaunchBootstrapStamp') -and
    ($setupPs1 -notmatch "Join-Path `$env:USERPROFILE '\.hermes'")
Add-StepResult -Name '7/8 setup gebruikt canonieke bootstrap stamp' -Ok $setupOk

# --- 8 install_rag_extras manifest guard ---
$extras = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/install_rag_extras.ps1')
$extrasOk = ($extras -match 'Test-HermesRagExtrasInstalled') -and
    ($extras -match 'Write-HermesRagDepsManifest')
Add-StepResult -Name '8/8 install_rag_extras verified manifest guard' -Ok $extrasOk

# --- Rapport ---
$status = if ($failures -eq 0) { 'PASS' } else { "FAIL ($failures)" }
$reportPath = Join-Path $scriptRoot ('HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E_REPORT_' + $reportStamp + '.md')
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Hermes Python institutional regression E2E - $status")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$sb.AppendLine("Repo: $RepoRoot")
[void]$sb.AppendLine("Python: $python")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('| Stap | OK | Detail |')
[void]$sb.AppendLine('|------|----|--------|')
foreach ($s in $steps) {
    $okMark = if ($s.Ok) { 'PASS' } else { 'FAIL' }
    $detail = if ($s.Detail) { $s.Detail.Replace('|', '/') } else { '' }
    [void]$sb.AppendLine("| $($s.Step) | $okMark | $detail |")
}
[void]$sb.AppendLine('')
[void]$sb.AppendLine('## Scope')
[void]$sb.AppendLine('- bootstrap stamp alleen na succesvolle RAG-sync')
[void]$sb.AppendLine('- rag-deps.json fast-path (rag_extras_verified)')
[void]$sb.AppendLine('- REPAIR non-interactive (geen Read-Host hang)')
[void]$sb.AppendLine('- HERMES_CONDA_ROOT + Get-HermesAuditPython resolver')
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== HERMES PYTHON INSTITUTIONAL REGRESSION E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== HERMES PYTHON INSTITUTIONAL REGRESSION E2E: PASS ===' -ForegroundColor Green
exit 0
