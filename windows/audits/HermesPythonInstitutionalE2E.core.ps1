# Institutioneel Python-beleid E2E (conda hermes-env, IDE sync, venv-quarantaine).
# Launcher: RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.ps1
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
    foreach ($candidate in @(
            (Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'),
            'python'
        )) {
        if ($candidate -eq 'python' -or (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }
    return 'python'
}

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

Write-Host '=== Hermes Python institutional E2E ===' -ForegroundColor Cyan
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$python = Get-HermesAuditPython

# --- 1 Repo artefacten ---
$repoFiles = @(
    'windows/HermesPythonPolicy.ps1',
    'windows/scripts/ensure_hermes_python.ps1',
    'windows/scripts/sync_hermes_ide_python.ps1',
    'windows/REPAIR_PYTHON.bat',
    'windows/scripts/launch_bootstrap.ps1',
    '.vscode/settings.json',
    'docs/HERMES_START.md',
    'tests/windows/test_hermes_python_institutional.py'
)
$artOk = $true
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $artOk = $false
        break
    }
}
Add-StepResult -Name '1/8 repo Python institutional artefacten' -Ok $artOk

# --- 2 Policy helpers aanwezig ---
$policyPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/HermesPythonPolicy.ps1')
$helperOk = ($policyPy -match 'function Update-HermesVscodeInterpreterPath') -and
    ($policyPy -match 'function Invoke-HermesSyncIdePython') -and
    ($policyPy -match 'try \{') -and
    ($policyPy -match 'Rename-Item')
Add-StepResult -Name '2/8 HermesPythonPolicy helpers + venv quarantaine catch' -Ok $helperOk

# --- 3 REPAIR + ensure wiring ---
$repairBat = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/REPAIR_PYTHON.bat')
$ensurePy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/ensure_hermes_python.ps1')
$wireOk = ($repairBat -match '-SyncIde') -and ($ensurePy -match 'SyncIde') -and ($ensurePy -match 'Invoke-HermesSyncIdePython')
Add-StepResult -Name '3/8 REPAIR/ensure IDE-sync wiring' -Ok $wireOk

# --- 4 .vscode portable interpreter ---
$settings = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath '.vscode/settings.json')
$vscodeOk = ($settings -match 'python.defaultInterpreterPath') -and
    ($settings -match 'hermes-env') -and
    ($settings -match 'activateEnvironment"\s*:\s*false')
Add-StepResult -Name '4/8 .vscode canonieke interpreter config' -Ok $vscodeOk

# --- 5 Isolated harness (8 scenario''s) ---
$harness = Join-Path $scriptRoot 'HermesPythonInstitutionalE2E.harness.ps1'
$harnessOk = Invoke-AuditCommand -Exe 'powershell' -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $harness
)
Add-StepResult -Name '5/8 isolated harness (8 scenario''s)' -Ok $harnessOk

# --- 6 pytest ---
if ($SkipPytest) {
    Add-StepResult -Name '6/8 pytest test_hermes_python_institutional' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $pytestOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/windows/test_hermes_python_institutional.py'),
        '-q', '--tb=short', '-o', 'addopts='
    )
    Add-StepResult -Name '6/8 pytest test_hermes_python_institutional' -Ok $pytestOk -Detail $python
}

# --- 7 runtime conda resolves ---
$condaPy = Get-HermesCondaPython
$runtimeOk = [bool]$condaPy -and (Test-HermesPythonHasPip -PythonExe $condaPy)
$condaDetail = if ($condaPy) { $condaPy } else { '' }
Add-StepResult -Name '7/8 runtime conda hermes-env + pip' -Ok $runtimeOk -Detail $condaDetail

# --- 8 docs institutional messaging ---
$startMd = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/HERMES_START.md')
$instMd = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/INSTITUTIONAL.md')
$docOk = ($startMd -match 'Python institutioneel') -and ($startMd -match 'REPAIR_PYTHON') -and ($instMd -match 'sync_hermes_ide_python')
Add-StepResult -Name '8/8 docs Python institutioneel' -Ok $docOk

# --- Rapport ---
$status = if ($failures -eq 0) { 'PASS' } else { "FAIL ($failures)" }
$reportFileName = 'HERMES_PYTHON_INSTITUTIONAL_E2E_REPORT_' + $reportStamp + '.md'
$reportPath = Join-Path $scriptRoot $reportFileName
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Hermes Python institutional E2E - $status")
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
[void]$sb.AppendLine('- conda hermes-env canoniek; repo .venv quarantaine zonder bootstrap-crash')
[void]$sb.AppendLine('- IDE sync via Update-HermesVscodeInterpreterPath / REPAIR_PYTHON -SyncIde')
[void]$sb.AppendLine('- pytest + harness edge cases (idempotent sync, missing key, env overrides)')
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== HERMES PYTHON INSTITUTIONAL E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== HERMES PYTHON INSTITUTIONAL E2E: PASS ===' -ForegroundColor Green
exit 0
