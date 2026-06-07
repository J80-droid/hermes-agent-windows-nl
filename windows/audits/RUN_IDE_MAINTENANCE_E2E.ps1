# E2E audit: IDE-onderhoudslandkaart (Windows PS1, upstream merge, LanceDB, renderer, skills/conda).
# Volledige keten voor fork-onderhoud; optioneel inclusief RUN_INSTITUTIONAL_E2E.
param(
    [switch]$ApplyDisplayFix,
    [switch]$IncludeInstitutional,
    [switch]$SkipMergePreview,
    [switch]$NoReport
)

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

# Continue: torch/RAG schrijft naar stderr zonder echte fout; exit-codes bepalen PASS/FAIL.
$ErrorActionPreference = 'Continue'
$scriptRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
Set-Location $repoRoot

$stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$reportLines = [System.Collections.Generic.List[string]]::new()
$stepTotal = if ($IncludeInstitutional) { 17 } elseif ($SkipMergePreview) { 15 } else { 16 }
$stepNum = 0
$failures = 0

function Add-ReportLine {
    param([string]$Line)
    [void]$script:reportLines.Add($Line)
}

function Write-StepHeader {
    param([string]$Title)
    $script:stepNum++
    $hdr = "=== $($script:stepNum)/$($script:stepTotal) $Title ==="
    Write-Host $hdr -ForegroundColor Cyan
    Add-ReportLine $hdr
}

function Step-Ok {
    param([string]$Msg)
    Write-Host ('[OK] ' + $Msg) -ForegroundColor Green
    Add-ReportLine "- **PASS** $Msg"
}

function Step-Fail {
    param([string]$Msg)
    Write-Host ('[FAIL] ' + $Msg) -ForegroundColor Red
    Add-ReportLine "- **FAIL** $Msg"
    $script:failures++
}

function Invoke-Tool {
    param([scriptblock]$Action)
    $null = & $Action 2>&1
    if ($null -eq $LASTEXITCODE) { return 0 }
    return [int]$LASTEXITCODE
}

function Find-CondaPython {
    foreach ($p in @(
            (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
            (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe')
        )) {
        if (-not ($p -and (Test-Path -LiteralPath $p))) { continue }
        $out = & $p run -n hermes-env python -c "import sys; print(sys.executable)" 2>&1
        if ($LASTEXITCODE -ne 0) { continue }
        $line = ($out | Select-Object -Last 1)
        if ($line) { return $line.ToString().Trim() }
    }
    throw 'hermes-env python niet beschikbaar (conda)'
}

$python = Find-CondaPython
Add-ReportLine "# IDE-onderhoud E2E - $stamp"
Add-ReportLine ""
Add-ReportLine "**Repo:** ``$repoRoot``"
Add-ReportLine ""

# --- 1 Repo artefacten ---
Write-StepHeader 'repo-artefacten (IDE-onderhoud)'
$required = @(
    'windows/verify_windows_script_chain.ps1',
    'windows/LANCEDB_MAINTENANCE.bat',
    'windows/scripts/run_lancedb_maintenance.ps1',
    'scripts/rag_pipeline/lancedb_maintenance.py',
    'scripts/audit_skill_drift.py',
    'windows/merge_upstream_fork.ps1',
    'windows/MERGE_UPSTREAM.bat',
    'windows/HermesSetupScriptPolicy.ps1',
    'windows/setup_hermes_windows.ps1',
    'scripts/windows/setup_hermes_windows.ps1',
    'scripts/diagnose_renderer.py',
    'scripts/score_institutional_render.py',
    'scripts/verify_institutional_guard.py',
    'tests/windows/test_merge_upstream_snippets.py',
    'tests/windows/test_apply_team_display_root.py',
    'tests/windows/test_status_bar_cost_e2e.py',
    'scripts/status_bar_cost_gateway_smoke.py',
    'tests/rag_pipeline/test_lancedb_maintenance.py',
    '.vscode/settings.json',
    '.cursor/rules/python-conda.mdc',
    '.cursor/rules/powershell-windows-paths.mdc'
)
$missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath $_)) })
if ($missing.Count -gt 0) {
    Step-Fail "Ontbrekende bestanden: $($missing -join ', ')"
} else {
    Step-Ok "$($required.Count) IDE-onderhoudsartefacten aanwezig"
}

# --- 2 Windows verify chain ---
Write-StepHeader 'verify_windows_script_chain'
$chain = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/verify_windows_script_chain.ps1'
& $chain
if ($LASTEXITCODE -ne 0) {
    Step-Fail 'verify_windows_script_chain.ps1'
} else {
    Step-Ok 'Windows script-keten + setup-wrapper + conda'
}

# --- 3 Setup wrapper pytest ---
Write-StepHeader 'pytest setup single-source'
Invoke-HermesAuditPytest -Python $python tests/windows/test_setup_single_canonical_ps1.py -q --tb=short
if ($LASTEXITCODE -ne 0) {
    Step-Fail 'test_setup_single_canonical_ps1'
} else {
    Step-Ok 'setup wrapper policy'
}

# --- 4 IDE maintenance pytest ---
Write-StepHeader 'pytest IDE-onderhoud (merge, lancedb, display)'
Invoke-HermesAuditPytest -Python $python `
    tests/windows/test_merge_upstream_snippets.py `
    tests/windows/test_apply_team_display_root.py `
    tests/windows/test_status_bar_cost_e2e.py `
    tests/rag_pipeline/test_lancedb_maintenance.py `
    tests/windows/test_merge_upstream_snippets.py::test_lancedb_maintenance_bat_exists `
    -q --tb=short
if ($LASTEXITCODE -ne 0) {
    Step-Fail 'IDE-onderhoud pytest subset'
} else {
    Step-Ok 'merge snippets + lancedb + team display + status bar cost'
}

# --- 5 LANCEDB list via bat ---
Write-StepHeader 'LANCEDB_MAINTENANCE.bat --list'
$prevEapBat = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$batList = cmd /c "windows\LANCEDB_MAINTENANCE.bat --list" 2>&1 | Out-String
$batCode = $LASTEXITCODE
$ErrorActionPreference = $prevEapBat
if ($batCode -ne 0) {
    Step-Fail "LANCEDB --list exit $LASTEXITCODE"
    Add-ReportLine "``````"
    Add-ReportLine $batList.Trim()
    Add-ReportLine "``````"
} elseif ($batList -notmatch 'Domeinen:') {
    Step-Fail 'LANCEDB --list: geen Domeinen-regel'
} else {
    $domLine = ($batList -split "`n" | Where-Object { $_ -match 'Domeinen:' } | Select-Object -First 1)
    Step-Ok "LANCEDB list ($domLine)"
}

# --- 6 LANCEDB inspect ---
Write-StepHeader 'LANCEDB_MAINTENANCE --inspect'
$maintPy = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'scripts/rag_pipeline/lancedb_maintenance.py'
$inspectOut = & $python $maintPy --inspect 2>&1 | Out-String
$inspectCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
if ($inspectOut -match '(?m)\[ACTIE\]') {
    Step-Fail 'LANCEDB --inspect (schema ACTIE op een of meer domeinen)'
} elseif ($inspectCode -ne 0) {
    Step-Fail "LANCEDB --inspect exit $inspectCode"
} else {
    Step-Ok 'LanceDB schema-audit alle domeinen'
}

# --- 7 Skill drift ---
Write-StepHeader 'audit_skill_drift.py'
$drift = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'scripts/audit_skill_drift.py'
& $python $drift
if ($LASTEXITCODE -ne 0) {
    Step-Fail 'skill/docs drift bevindingen'
} else {
    Step-Ok 'geen skill drift in fork-scope'
}

# --- 8 Merge git-diff snippet smoke (pytest) ---
Write-StepHeader 'merge_upstream git-diff snippet'
Invoke-HermesAuditPytest -Python $python tests/windows/test_merge_upstream_snippets.py::test_git_diff_snippet_returns_content -q --tb=short
if ($LASTEXITCODE -ne 0) {
    Step-Fail 'Get-ConflictSnippetFromGitDiff smoke'
} else {
    Step-Ok 'merge snippet helper (git diff)'
}

# --- 9 MERGE_UPSTREAM -PromptOnly ---
if (-not $SkipMergePreview) {
    Write-StepHeader 'MERGE_UPSTREAM.bat -PromptOnly'
    $mergeBat = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/MERGE_UPSTREAM.bat'
    $env:HERMES_NONINTERACTIVE = '1'
    $env:HERMES_SKIP_PAUSE_AFTER_UPDATE = '1'
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $mergeOut = cmd /c "`"$mergeBat`" -PromptOnly -NoPrompt" 2>&1 | Out-String
    $mergeCode = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($mergeCode -ne 0 -and $mergeCode -ne 5) {
        Step-Fail "MERGE_UPSTREAM -PromptOnly exit $mergeCode"
        Add-ReportLine $mergeOut.Trim()
    } else {
        if ($mergeOut -match 'Al gelijk met upstream|Geen voorspelde|voorspeld') {
            Step-Ok 'MERGE_UPSTREAM preview (upstream remote OK)'
        } else {
            Step-Ok 'MERGE_UPSTREAM -PromptOnly uitgevoerd'
        }
    }
} else {
    Add-ReportLine "- **SKIP** MERGE_UPSTREAM -PromptOnly"
}

# --- 10 Display fix (optioneel) ---
if ($ApplyDisplayFix) {
    Write-StepHeader 'apply_team_display (optioneel)'
    & (Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/apply_team_display.ps1')
    if ($LASTEXITCODE -ne 0) {
        Step-Fail 'apply_team_display.ps1'
    } else {
        Step-Ok 'team display defaults toegepast'
    }
}

# --- 11 diagnose_renderer ---
Write-StepHeader 'diagnose_renderer.py --verify'
$diag = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'scripts/diagnose_renderer.py'
& $python $diag --verify
if ($LASTEXITCODE -ne 0) {
  if (-not $ApplyDisplayFix) {
        Write-Host '[INFO] Eerste poging mislukt - auto-fix team display...' -ForegroundColor Yellow
        & (Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/apply_team_display.ps1')
        & $python $diag --verify
    }
    if ($LASTEXITCODE -ne 0) {
        Step-Fail 'diagnose_renderer --verify (display drift?)'
    } else {
        Step-Ok 'diagnose_renderer na auto-fix display'
    }
} else {
    Step-Ok 'diagnose_renderer institutional_rich + demo'
}

# --- 12 score ---
Write-StepHeader 'score_institutional_render.py --verify'
$score = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'scripts/score_institutional_render.py'
& $python $score --verify
if ($LASTEXITCODE -ne 0) {
    Step-Fail 'score onder drempel 9.0'
} else {
    Step-Ok 'render score minimaal 9.0'
}

# --- 13 normalizer pariteit ---
Write-StepHeader 'pytest normalizer TS pariteit'
Invoke-HermesAuditPytest -Python $python tests/overlay/test_normalizer_ts_parity.py -q --tb=short
if ($LASTEXITCODE -ne 0) {
    Step-Fail 'test_normalizer_ts_parity'
} else {
    Step-Ok 'Python ↔ TS normalizer pariteit'
}

# --- 14 institutional guard (skip of subset; geen --force) ---
Write-StepHeader 'verify_institutional_guard'
$guard = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'scripts/verify_institutional_guard.py'
$guardOut = & $python $guard 2>&1 | Out-String
$guardCode = $LASTEXITCODE
if ($guardCode -ne 0) {
    Step-Fail 'verify_institutional_guard'
} elseif ($guardOut -match 'guard overgeslagen|OK') {
    Step-Ok 'institutional guard (skip of subset bij geen diff)'
} else {
    Step-Ok 'institutional guard tests na renderer-wijziging'
}

# --- 15 IDE conda config ---
Write-StepHeader 'IDE conda interpreter config'
$vscode = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath '.vscode/settings.json'
$vsText = Get-Content -LiteralPath $vscode -Raw -Encoding UTF8
if ($vsText -notmatch 'hermes-env' -or $vsText -notmatch 'python\.exe') {
    Step-Fail '.vscode/settings.json mist hermes-env python pad'
} else {
    Step-Ok '.vscode hermes-env python pad'
}
$condaRule = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath '.cursor/rules/python-conda.mdc'
if (-not (Test-Path -LiteralPath $condaRule)) {
    Step-Fail 'python-conda.mdc ontbreekt'
} else {
    Step-Ok 'Cursor rule python-conda.mdc'
}

# --- 16 LanceDB benchmark (informatief) ---
Write-StepHeader 'LANCEDB benchmark informatief 500ms'
$benchCode = Invoke-Tool { & $python $maintPy --benchmark --domain core --queries 3 --max-ms 500 }
if ($benchCode -ne 0) {
    Add-ReportLine '- **WARN** benchmark p95 boven 500ms op minstens een domein (geen hard fail voor fork)'
    Write-Host 'WARN benchmark boven 500ms - zie output' -ForegroundColor Yellow
} else {
    Step-Ok 'benchmark binnen 500ms (relaxed NFR-poort)'
}

# --- 17-18 optioneel institutioneel ---
if ($IncludeInstitutional) {
    Write-StepHeader 'RUN_INSTITUTIONAL_E2E (volledig)'
    & (Join-Path $scriptRoot 'RUN_INSTITUTIONAL_E2E.ps1')
    if ($LASTEXITCODE -ne 0) {
        Step-Fail 'RUN_INSTITUTIONAL_E2E'
    } else {
        Step-Ok 'institutioneel E2E 11/11'
    }
}

# --- Rapport ---
Add-ReportLine ""
if ($failures -gt 0) {
    Add-ReportLine "## Resultaat: **FAIL** - ${failures} stappen gefaald"
    Write-Host ''
    Write-Host "=== IDE MAINTENANCE E2E: FAIL ($failures) ===" -ForegroundColor Red
} else {
    Add-ReportLine "## Resultaat: **PASS**"
    Write-Host ""
    Write-Host '=== IDE MAINTENANCE E2E: PASS ===' -ForegroundColor Green
}

if (-not $NoReport) {
    $reportPath = Join-Path $scriptRoot "IDE_MAINTENANCE_E2E_REPORT_$stamp.md"
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($reportPath, ($reportLines -join "`n") + "`n", $utf8)
    Write-Host "[INFO] Rapport: $reportPath" -ForegroundColor Cyan
}

if ($failures -gt 0) { exit 1 }
exit 0
