# Upstream sync fase-2 E2E: git merge vóór hermes update, pip na merge, preflight fetch-skip, TUI layout.
# Launcher: RUN_UPSTREAM_SYNC_PHASE2_E2E.ps1
param(
    [string]$RepoRoot = '',
    [switch]$SkipVitest
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

function Ensure-HermesInkBuilt {
    param([string]$UiRoot)
    $inkDist = Join-Path $UiRoot 'packages/hermes-ink/dist/entry-exports.js'
    if (Test-Path -LiteralPath $inkDist) { return $true }
    Write-Host '[INFO] @hermes/ink dist ontbreekt — build...' -ForegroundColor Cyan
    Push-Location (Join-Path $UiRoot 'packages/hermes-ink')
    try {
        & npm run build 2>&1 | Out-Host
        return ($LASTEXITCODE -eq 0) -and (Test-Path -LiteralPath $inkDist)
    } finally {
        Pop-Location
    }
}

Write-Host '=== Upstream Sync Phase 2 E2E ===' -ForegroundColor Cyan
Write-Host "[INFO] Repo: $RepoRoot" -ForegroundColor Cyan
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

# --- 1 Artefacten ---
$artifacts = @(
    'windows/upstream_sync.ps1',
    'windows/UPSTREAM_SYNC.md',
    'ui-tui/src/domain/usageCostBar.ts',
    'ui-tui/src/components/appChrome.tsx',
    'windows/audits/UpstreamSyncPhase2E2E.core.ps1',
    'windows/audits/UpstreamSyncPhase2E2E.harness.py',
    'windows/audits/RUN_UPSTREAM_SYNC_PHASE2_E2E.ps1',
    'windows/audits/RUN_UPSTREAM_SYNC_PHASE2_E2E.bat'
)
$missing = @($artifacts | Where-Object {
    -not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $_))
})
Add-StepResult '1/8 repo artefacten' ($missing.Count -eq 0) $(if ($missing.Count) { $missing -join ', ' } else { "$($artifacts.Count) bestanden" })

# --- 2 upstream_sync merge + pip wiring ---
$sync = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/upstream_sync.ps1')
$mergeWiring = ($sync -match 'function Invoke-UpstreamGitMergeIfBehind') -and
    ($sync -match '\$script:UpstreamPreflightFetched\s*=\s*\$true') -and
    ($sync -match 'if\s*\(-not\s*\$script:UpstreamPreflightFetched\)') -and
    ($sync -match 'git rev-parse --verify upstream/main') -and
    ($sync -match 'Test-NativeCommandFailed') -and
    ($sync -match 'function Install-HermesEditablePythonAfterUpstreamMerge') -and
    ($sync -match '\$script:LastUpstreamMergedCount\s*-\s*gt\s*0') -and
    ($sync -match '\$mergeCode\s*=\s*Invoke-UpstreamGitMergeIfBehind')
Add-StepResult '2/8 upstream_sync merge + preflight fetch-skip + pip hook' $mergeWiring

# --- 3 Invoke-HermesUpdate volgorde ---
$hermesBlock = [regex]::Match(
    $sync,
    '(?s)function Invoke-HermesUpdate\s*\{.*?(?=function |\z)'
).Value
$orderOk = $false
if ($hermesBlock) {
    $mergePos = $hermesBlock.IndexOf('Invoke-UpstreamGitMergeIfBehind')
    $pipPos = $hermesBlock.IndexOf('Install-HermesEditablePythonAfterUpstreamMerge')
    $hermesPos = $hermesBlock.IndexOf("'hermes', 'update'")
    $orderOk = ($mergePos -ge 0) -and ($hermesPos -ge 0) -and ($mergePos -lt $hermesPos) -and
        (($pipPos -lt 0) -or (($pipPos -gt $mergePos) -and ($pipPos -lt $hermesPos)))
}
Add-StepResult '3/8 Invoke-HermesUpdate: merge, pip (indien), hermes update' $orderOk

# --- 4 TUI status-rule alignment ---
$usage = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'ui-tui/src/domain/usageCostBar.ts')
$app = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'ui-tui/src/components/appChrome.tsx')
$tuiOk = ($usage -match 'export function statusRuleMinLeftWidth') -and
    ($usage -match 'leftWidth\?:') -and
    ($usage -match 'STATUS_RULE_NON_COST_RESERVE') -and
    ($app -match 'statusRuleMinLeftWidth') -and
    ($app -match 'leftWidth,') -and
    ($app -match 'cwdReserve:\s*rightWidth\s*\+\s*separatorWidth')
Add-StepResult '4/8 TUI statusRuleMinLeftWidth + leftWidth doorgeven' $tuiOk

# --- 5 UPSTREAM_SYNC.md ---
$md = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/UPSTREAM_SYNC.md')
$docsOk = ($md -match 'Invoke-UpstreamGitMergeIfBehind') -and
    ($md -match 'git merge upstream/main') -and
    ($md -match 'hermes update')
Add-StepResult '5/8 UPSTREAM_SYNC.md fase-2 documentatie' $docsOk

# --- 6 Vitest ---
if (-not $SkipVitest) {
    $uiRoot = Join-Path $RepoRoot 'ui-tui'
    $inkOk = Ensure-HermesInkBuilt -UiRoot $uiRoot
    if (-not $inkOk) {
        Add-StepResult '6/8 vitest statusRule + usageCostBar' $false 'hermes-ink build mislukt'
    } else {
        Push-Location $uiRoot
        try {
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            & npx vitest run statusRule usageCostBar 2>&1 | Out-Host
            $vitestOk = ($LASTEXITCODE -eq 0)
            $ErrorActionPreference = $prevEap
        } finally {
            Pop-Location
        }
        Add-StepResult '6/8 vitest statusRule + usageCostBar' $vitestOk
    }
} else {
    Add-StepResult '6/8 vitest statusRule + usageCostBar' $true 'overgeslagen (-SkipVitest)'
}

# --- 7 Python harness ---
$harness = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/audits/UpstreamSyncPhase2E2E.harness.py'
$harnessOk = Invoke-AuditCommand -Exe $python -ArgumentList @($harness)
Add-StepResult '7/8 python harness (merge/pip/TUI volgorde)' $harnessOk $python

# --- 8 UPDATE_HERMES.bat roept upstream_sync aan ---
$updateBat = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/UPDATE_HERMES.bat')
$chainOk = ($updateBat -match 'upstream_sync\.ps1')
Add-StepResult '8/8 UPDATE_HERMES.bat roept upstream_sync aan' $chainOk

# --- Rapport ---
$status = if ($failures -eq 0) { 'PASS' } else { "FAIL ($failures)" }
$reportPath = Join-Path $scriptRoot ('UPSTREAM_SYNC_PHASE2_E2E_REPORT_' + $stamp + '.md')
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Upstream Sync Phase 2 E2E - $status")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$sb.AppendLine("Repo: $RepoRoot")
[void]$sb.AppendLine("Python: $python")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("| Stap | OK | Detail |")
[void]$sb.AppendLine("|------|----|--------|")
foreach ($s in $steps) {
    $okMark = if ($s.Ok) { 'PASS' } else { 'FAIL' }
    $detail = if ($s.Detail) { $s.Detail.Replace([char]124, '/') } else { '' }
    [void]$sb.AppendLine("| $($s.Step) | $okMark | $detail |")
}
[void]$sb.AppendLine('')
[void]$sb.AppendLine('## E2E-scenarios')
[void]$sb.AppendLine('- Preflight zet UpstreamPreflightFetched; merge slaat dubbele fetch over')
[void]$sb.AppendLine('- Invoke-UpstreamGitMergeIfBehind: verify upstream/main, rev-list exitcode, MERGE_HEAD guard')
[void]$sb.AppendLine('- Na merge: pip install -e . vóór hermes update (origin up-to-date edge case)')
[void]$sb.AppendLine('- TUI: gedeelde statusRuleMinLeftWidth + leftWidth voor cost-tier')
[void]$sb.AppendLine('- Vitest + Python harness + UPDATE_HERMES keten')
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== UPSTREAM SYNC PHASE 2 E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== UPSTREAM SYNC PHASE 2 E2E: PASS ===' -ForegroundColor Green
exit 0
