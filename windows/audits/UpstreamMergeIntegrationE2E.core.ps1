# Upstream merge integration E2E — status-rule cwdReserve + profile create (s6 + strip model).
param(
    [string]$RepoRoot = '',
    [switch]$SkipVitest,
    [switch]$SkipPytest
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
$windowsRoot = (Resolve-Path (Join-Path $scriptRoot '..')).Path
. (Join-Path $windowsRoot 'HermesShellCommon.ps1')

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
        $out = & $conda run -n hermes-env python -c 'import sys; print(sys.executable)'
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
        Write-HermesOk ($Name + $suffix)
    } else {
        Write-HermesFail ($Name + $suffix)
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
    $out = & $Exe @ArgumentList
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEap
    foreach ($line in @($out)) {
        if ($null -ne $line -and "$line".Trim()) {
            Write-Host $line
        }
    }
    return $ok
}

Write-Host '=== Upstream Merge Integration E2E ===' -ForegroundColor Cyan
Write-HermesInfo ('Repo: ' + $RepoRoot)
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

$repoArtifacts = @(
    'ui-tui/src/domain/usageCostBar.ts',
    'ui-tui/src/components/appChrome.tsx',
    'ui-tui/src/__tests__/statusRule.test.ts',
    'ui-tui/src/__tests__/usageCostBar.test.ts',
    'hermes_cli/profiles.py',
    'windows/audits/UpstreamMergeIntegrationE2E.harness.py',
    'windows/audits/UpstreamMergeIntegrationE2E.core.ps1',
    'windows/audits/RUN_UPSTREAM_MERGE_INTEGRATION_E2E.ps1'
)
$missing = @($repoArtifacts | Where-Object {
    -not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $_))
})
$detail1 = if ($missing.Count) { ($missing -join ', ') } else { "$($repoArtifacts.Count) bestanden" }
Add-StepResult '1/10 repo artefacten' ($missing.Count -eq 0) $detail1

$appChrome = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'ui-tui/src/components/appChrome.tsx')
$usageCost = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'ui-tui/src/domain/usageCostBar.ts')
$profilesPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'hermes_cli/profiles.py')
$upstreamSync = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/upstream_sync.ps1')
$upstreamMergeOk = ($upstreamSync -match 'function Invoke-UpstreamGitMergeIfBehind') -and
    ($upstreamSync -match 'Invoke-UpstreamGitMergeIfBehind') -and
    ($upstreamSync -match 'git merge upstream/main')

$wiringOk = ($appChrome -match 'cwdReserve:\s*rightWidth\s*\+\s*separatorWidth') -and
    ($appChrome -match 'statusRuleWidths\(ruleCols') -and
    ($usageCost -match 'cwdReserve\?') -and
    ($usageCost -match 'stringWidth') -and
    ($profilesPy -match 'except ImportError:') -and
    ($profilesPy -match '_maybe_register_gateway_service\(canon\)') -and
    $upstreamMergeOk
Add-StepResult '2/10 bron wiring + upstream_sync merge' $wiringOk

$mergePs1 = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/merge_upstream_fork.ps1')
$upstreamMd = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/UPSTREAM_SYNC.md')
$profilesMd = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'website/docs/user-guide/profiles.md')
$docsOk = ($mergePs1 -match 'usageCostBar.ts') -and ($mergePs1 -match 'status_bar_cost.py') -and
    ($upstreamMd -match 'usageCostBar') -and ($profilesMd -match 'Model inheritance') -and ($profilesMd -match 's6-overlay')
Add-StepResult '3/10 merge/docs guardrails' $docsOk

if (-not $SkipVitest) {
    $vitestRc = Invoke-HermesUiTuiVitest -RepoRoot $RepoRoot -TestPaths @('statusRule', 'usageCostBar')
    if ($vitestRc -eq 2) {
        Add-StepResult '4/10 vitest statusRule + usageCostBar' $true 'overgeslagen (geen npm)'
    } else {
        Add-StepResult '4/10 vitest statusRule + usageCostBar' ($vitestRc -eq 0)
    }
} else {
    Add-StepResult '4/10 vitest statusRule + usageCostBar' $true 'overgeslagen (-SkipVitest)'
}

if (-not $SkipPytest) {
    Push-Location $RepoRoot
    try {
        Invoke-HermesAuditPytest -Python $python `
            tests/windows/test_upstream_merge_integration_e2e.py `
            tests/hermes_cli/test_profiles_s6_hooks.py `
            tests/hermes_cli/test_profile_model_inheritance.py::test_strip_model_block `
            -q --tb=line
    } finally {
        Pop-Location
    }
    Add-StepResult '5/10 pytest profile + s6 hooks' ($LASTEXITCODE -eq 0) $python
} else {
    Add-StepResult '5/10 pytest profile + s6 hooks' $true 'overgeslagen (-SkipPytest)'
}

$harness = Join-Path $scriptRoot 'UpstreamMergeIntegrationE2E.harness.py'
Push-Location $RepoRoot
try {
    & $python $harness
} finally {
    Pop-Location
}
Add-StepResult '6/10 harness (source + create_profile strip)' ($LASTEXITCODE -eq 0)

$noConflictMarkers = ($appChrome -notmatch '^<<<<<<< ') -and
    ($usageCost -notmatch '^<<<<<<< ') -and
    ($profilesPy -notmatch '^<<<<<<< ')
Add-StepResult '7/10 geen merge-conflict markers in kernbestanden' $noConflictMarkers

$profilesCompile = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'hermes_cli/profiles.py'
& $python -m py_compile $profilesCompile 2>$null
Add-StepResult '8/10 py_compile profiles.py' ($LASTEXITCODE -eq 0)

$null = git -C $RepoRoot merge-base --is-ancestor upstream/main HEAD 2>$null
$syncOk = ($LASTEXITCODE -eq 0)
if (-not $syncOk) {
    git -C $RepoRoot fetch upstream --quiet 2>$null
    git -C $RepoRoot merge-base --is-ancestor upstream/main HEAD 2>$null
    $syncOk = ($LASTEXITCODE -eq 0)
}
$behind = 0
if ($syncOk) {
    $behind = [int](git -C $RepoRoot rev-list --count HEAD..upstream/main 2>$null)
}
$gitDetail = if ($syncOk) { "upstream/main ancestor; behind=$behind" } else { 'upstream niet gemerged in HEAD' }
Add-StepResult '9/10 git: upstream/main in HEAD' ($syncOk -and $behind -eq 0) $gitDetail

$runnerBat = Join-Path $scriptRoot 'RUN_UPSTREAM_MERGE_INTEGRATION_E2E.bat'
$runnerOk = (Test-Path -LiteralPath $runnerBat) -and (Test-Path -LiteralPath (Join-Path $scriptRoot 'RUN_UPSTREAM_MERGE_INTEGRATION_E2E.ps1'))
Add-StepResult '10/10 audit runners (.bat + .ps1)' $runnerOk

$reportFile = 'UPSTREAM_MERGE_INTEGRATION_E2E_REPORT_' + $stamp + '.md'
$reportPath = Join-Path $scriptRoot $reportFile
$status = if ($failures -eq 0) { 'PASS' } else { 'FAIL' }
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Upstream Merge Integration E2E - $status")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$sb.AppendLine("Repo: ``$RepoRoot``")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('| Stap | Status | Detail |')
[void]$sb.AppendLine('|------|--------|--------|')
foreach ($s in $steps) {
    $st = if ($s.Ok) { 'PASS' } else { 'FAIL' }
    $det = ($s.Detail -replace '\|', '/') -replace "`r?`n", ' '
    [void]$sb.AppendLine("| $($s.Step) | $st | $det |")
}
[void]$sb.AppendLine('')
if ($failures -gt 0) {
    [void]$sb.AppendLine("**$failures** stap(pen) gefaald. Herstel code en run ``windows\audits\RUN_UPSTREAM_MERGE_INTEGRATION_E2E.bat`` opnieuw.")
} else {
    [void]$sb.AppendLine('Alle stappen geslaagd. Optioneel: ``windows\REBUILD_TUI.bat`` + nieuwe Hermes-sessie.')
}
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host ''
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== UPSTREAM MERGE INTEGRATION E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== UPSTREAM MERGE INTEGRATION E2E: PASS ===' -ForegroundColor Green
exit 0
