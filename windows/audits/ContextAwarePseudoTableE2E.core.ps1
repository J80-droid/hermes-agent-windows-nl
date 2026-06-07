# Context-aware pseudo-tabel normalizer E2E (overview 2-6 kolommen, intent routing, streaming).
# Launcher: RUN_CONTEXT_AWARE_PSEUDO_TABLE_E2E.ps1
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest,
    [switch]$SkipTsParity
)

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

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

Write-Host '=== Context-aware pseudo-tabel normalizer E2E ===' -ForegroundColor Cyan
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

# --- 1 Repo artefacten ---
$repoFiles = @(
    'overlay/hermes_cli/markdown_output_normalize.py',
    'web/src/lib/institutionalMarkdown.ts',
    'cli.py',
    'scripts/verify_pseudo_table_normalizer.py',
    'scripts/diagnose_renderer.py',
    'docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md',
    'docs/INSTITUTIONAL_PRESENTATION.md',
    'tests/overlay/test_markdown_output_normalize.py',
    'tests/overlay/test_normalizer_ts_parity.py',
    'windows/audits/ContextAwarePseudoTableE2E.harness.py',
    'windows/audits/ContextAwarePseudoTableE2E.core.ps1',
    'windows/audits/RUN_CONTEXT_AWARE_PSEUDO_TABLE_E2E.ps1'
)
$repoOk = $true
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $repoOk = $false
        break
    }
}
Add-StepResult -Name '1/12 repo context-aware normalizer artefacten' -Ok $repoOk

# --- 2 Python overview parser wiring ---
$pyNorm = Read-HermesRepoText -Path (Join-HermesForkModulePath -RepoRoot $RepoRoot -RelativePath 'hermes_cli/markdown_output_normalize.py')
$pyOk = ($pyNorm -match 'def _parse_overview_body_to_rows') -and
    ($pyNorm -match 'def _infer_section_intent') -and
    ($pyNorm -match 'def _parse_section_to_table') -and
    ($pyNorm -match 'intent: str \| None = None') -and
    ($pyNorm -match '_parse_section_to_table\(heading, body_lines, intent\)')
Add-StepResult -Name '2/12 python overview parser + intent routing' -Ok $pyOk

# --- 3 TS parity overview wiring ---
$tsNorm = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'web/src/lib/institutionalMarkdown.ts')
$tsOk = ($tsNorm -match 'function parseOverviewBodyToRows') -and
    ($tsNorm -match 'function inferSectionIntent') -and
    ($tsNorm -match 'function parseSectionToTable') -and
    ($tsNorm -match 'parseSectionToTable\(heading, bodyLines, intent\)')
Add-StepResult -Name '3/12 web TS overview parser + intent routing' -Ok $tsOk

# --- 4 CLI streaming flush wiring ---
$cliPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'cli.py')
$cliOk = ($cliPy -match 'def _prepare_stream_table_block') -and
    ($cliPy -match 'assistant_render_style') -and
    ($cliPy -match 'normalize_assistant_markdown\(joined\)') -and
    ($cliPy -match 'self\._prepare_stream_table_block\(joined\)')
Add-StepResult -Name '4/12 CLI streaming eind-flush normalisatie' -Ok $cliOk

# --- 5 Isolated harness (8 scenario''s) ---
$harness = Join-Path $scriptRoot 'ContextAwarePseudoTableE2E.harness.py'
$harnessOk = Invoke-AuditCommand -Exe $python -ArgumentList @($harness)
Add-StepResult -Name '5/12 isolated harness (9 scenario''s)' -Ok $harnessOk

# --- 6 Pytest overview unit tests ---
if ($SkipPytest) {
    Add-StepResult -Name '6/12 pytest overview normalizer unit' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $overviewOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/overlay/test_markdown_output_normalize.py'),
        '-k', 'overview or auxiliary_overview or separator_between_groups',
        '-q',
        '--tb=short',
        '-o', 'addopts='
    )
    Add-StepResult -Name '6/12 pytest overview normalizer unit' -Ok $overviewOk -Detail $python
}

# --- 7 Pytest TS parity overview fixtures ---
if ($SkipPytest -or $SkipTsParity) {
    $skipDetail = if ($SkipTsParity) { 'overgeslagen (-SkipTsParity)' } else { 'overgeslagen (-SkipPytest)' }
    Add-StepResult -Name '7/12 pytest TS parity overview fixtures' -Ok $true -Detail $skipDetail
} else {
    $parityOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/overlay/test_normalizer_ts_parity.py'),
        '-k', 'auxiliary_overview_4col or auxiliary_overview_2col',
        '-q',
        '--tb=short',
        '-o', 'addopts='
    )
    Add-StepResult -Name '7/12 pytest TS parity overview fixtures' -Ok $parityOk
}

# --- 8 verify_pseudo_table_normalizer (incl. 4-koloms probe) ---
$verifyPy = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/verify_pseudo_table_normalizer.py'
$verifyOk = Invoke-AuditCommand -Exe $python -ArgumentList @($verifyPy, '--verify')
Add-StepResult -Name '8/12 verify_pseudo_table_normalizer --verify' -Ok $verifyOk

# --- 9 diagnose_renderer overview pseudo warning ---
$diagPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/diagnose_renderer.py')
$diagOk = ($diagPy -match 'overzicht\|auxiliary') -and
    ($diagPy -match 'Label:-regels zonder markdown-tabel')
Add-StepResult -Name '9/12 diagnose_renderer overview pseudo warning' -Ok $diagOk

# --- 10 SOUL + presentation docs ---
$soulText = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md')
$presText = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/INSTITUTIONAL_PRESENTATION.md')
$docsOk = ($soulText -match 'Overzicht per auxiliary taak') -and
    ($soulText -match 'Provider \| Model \| Base URL') -and
    ($presText -match 'Overzicht per auxiliary taak') -and
    ($presText -match 'context 2.6 kolommen|contextafhankelijk 2')
Add-StepResult -Name '10/12 SOUL + presentation overview docs' -Ok $docsOk

# --- 11 py_compile modified modules ---
$compileTargets = @(
    'overlay/hermes_cli/markdown_output_normalize.py',
    'scripts/verify_pseudo_table_normalizer.py',
    'scripts/diagnose_renderer.py',
    'windows/audits/ContextAwarePseudoTableE2E.harness.py'
)
$compileOk = $true
foreach ($rel in $compileTargets) {
    $target = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel
    & $python -m py_compile $target 2>$null
    if ($LASTEXITCODE -ne 0) {
        $compileOk = $false
        break
    }
}
Add-StepResult -Name '11/12 py_compile modified python modules' -Ok $compileOk

# --- 12 Regressie vs/Cloud-Lokaal ---
if ($SkipPytest) {
    Add-StepResult -Name '12/12 pytest vs/cloud regressie' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $regOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/overlay/test_markdown_output_normalize.py'),
        '-k', 'ollama_vs or auxiliary_tasks or pseudo_idempotent_on_valid_comparison',
        '-q',
        '--tb=short',
        '-o', 'addopts='
    )
    Add-StepResult -Name '12/12 pytest vs/cloud regressie' -Ok $regOk
}

# --- Rapport ---
$reportFileName = 'CONTEXT_AWARE_PSEUDO_TABLE_E2E_REPORT_' + $reportStamp + '.md'
$reportPath = Join-Path $scriptRoot $reportFileName
$status = if ($failures -eq 0) { 'PASS' } else { 'FAIL' }
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Context-aware pseudo-tabel normalizer E2E - $status")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$sb.AppendLine("Repo: ``$RepoRoot``")
[void]$sb.AppendLine("Python: ``$python``")
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
    [void]$sb.AppendLine("**$failures** stap(pen) gefaald.")
} else {
    [void]$sb.AppendLine('Alle stappen geslaagd. Context-aware pseudo-tabellen (2-6 kolommen) worden deterministisch omgezet vóór render.')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('Scenario''s: 4-koloms auxiliary grouped/collapsed, 2-koloms config, vs/Cloud regressie, scheiding tussen groepen, TS parity, streaming flush.')
}
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host ''
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== CONTEXT-AWARE PSEUDO-TABEL E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== CONTEXT-AWARE PSEUDO-TABEL E2E: PASS ===' -ForegroundColor Green
exit 0
