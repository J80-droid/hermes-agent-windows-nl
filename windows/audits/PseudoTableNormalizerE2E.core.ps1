# Pseudo-tabel normalizer E2E core (underscore/vs → markdown-tabel, turn-onafhankelijk).
# Launcher: RUN_PSEUDO_TABLE_NORMALIZER_E2E.ps1
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
            'C:\Users\jamel\miniconda3\envs\hermes-env\python.exe',
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

Write-Host '=== Pseudo-tabel normalizer E2E ===' -ForegroundColor Cyan
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

# --- 1 Repo artefacten ---
$repoFiles = @(
    'hermes_cli/markdown_output_normalize.py',
    'web/src/lib/institutionalMarkdown.ts',
    'ui-tui/src/lib/institutionalMarkdownNormalize.ts',
    'scripts/normalize_assistant_markdown_ts_runner.ts',
    'scripts/normalize_assistant_markdown_ink_runner.ts',
    'scripts/diagnose_renderer.py',
    'scripts/score_institutional_render.py',
    'scripts/verify_institutional_guard.py',
    'scripts/verify_pseudo_table_normalizer.py',
    'docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md',
    'tests/hermes_cli/test_markdown_output_normalize.py',
    'tests/hermes_cli/test_normalizer_ts_parity.py',
    'tests/cli/test_institutional_rich_render.py',
    'windows/audits/PseudoTableNormalizerE2E.core.ps1',
    'windows/audits/RUN_PSEUDO_TABLE_NORMALIZER_E2E.ps1'
)
$repoOk = $true
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $repoOk = $false
        break
    }
}
Add-StepResult -Name '1/10 repo pseudo-tabel artefacten' -Ok $repoOk

# --- 2 Python pipeline wiring ---
$pyNorm = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'hermes_cli/markdown_output_normalize.py')
$pyOk = ($pyNorm -match 'def ensure_markdown_table_dividers') -and
    ($pyNorm -match 'def normalize_pseudo_tables_to_markdown') -and
    ($pyNorm -match 'ensure_markdown_table_dividers\(out\)') -and
    ($pyNorm -match 'normalize_pseudo_tables_to_markdown\(out\)') -and
    ($pyNorm -match '_append_dual_entity_row')
Add-StepResult -Name '2/10 python normalizer pipeline' -Ok $pyOk

# --- 3 Web/Ink parity wiring ---
$tsNorm = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'web/src/lib/institutionalMarkdown.ts')
$inkNorm = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'ui-tui/src/lib/institutionalMarkdownNormalize.ts')
$tsOk = ($tsNorm -match 'function ensureMarkdownTableDividers') -and
    ($tsNorm -match 'function normalizePseudoTablesToMarkdown') -and
    ($tsNorm -match 'ensureMarkdownTableDividers\(out\)') -and
    ($tsNorm -match 'normalizePseudoTablesToMarkdown\(out\)') -and
    ($inkNorm -match 'institutionalMarkdown\.ts')
Add-StepResult -Name '3/10 web/ink parity wiring' -Ok $tsOk

# --- 4 SOUL + troubleshooting docs ---
$soulPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md'
$presPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/INSTITUTIONAL_PRESENTATION.md'
$soulText = Read-HermesRepoText -Path $soulPath
$presText = Read-HermesRepoText -Path $presPath
$docsOk = ($soulText -match 'pseudo-layout') -and
    ($soulText -match 'Tabellen: markdown \|---\|') -and
    ($soulText -match 'Ollama versus LM Studio') -and
    ($presText -match 'Pseudo-tabel / underscore-vergelijking')
Add-StepResult -Name '4/10 SOUL + presentation docs' -Ok $docsOk

# --- 5 Pytest normalizer unit ---
if ($SkipPytest) {
    Add-StepResult -Name '5/10 pytest markdown_output_normalize' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $normOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/hermes_cli/test_markdown_output_normalize.py'),
        '-q',
        '--tb=short',
        '-o', 'addopts='
    )
    Add-StepResult -Name '5/10 pytest markdown_output_normalize' -Ok $normOk -Detail $python
}

# --- 6 Pytest TS parity (pseudo fixtures) ---
if ($SkipPytest -or $SkipTsParity) {
    $skipDetail = if ($SkipTsParity) { 'overgeslagen (-SkipTsParity)' } else { 'overgeslagen (-SkipPytest)' }
    Add-StepResult -Name '6/10 pytest ts parity pseudo fixtures' -Ok $true -Detail $skipDetail
} else {
    $parityOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/hermes_cli/test_normalizer_ts_parity.py'),
        '-k', 'ollama_vs_lm_studio_underscore or auxiliary_tasks_pseudo or pipe_rows_missing_divider',
        '-q',
        '--tb=short',
        '-o', 'addopts='
    )
    Add-StepResult -Name '6/10 pytest ts parity pseudo fixtures' -Ok $parityOk
}

# --- 7 Pytest rich render pseudo ---
if ($SkipPytest) {
    Add-StepResult -Name '7/10 pytest rich render pseudo' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $richOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/cli/test_institutional_rich_render.py'),
        '-k', 'pseudo_comparison',
        '-q',
        '--tb=short',
        '-o', 'addopts='
    )
    Add-StepResult -Name '7/10 pytest rich render pseudo' -Ok $richOk
}

# --- 8 diagnose_renderer --verify (incl. pseudo self-test) ---
$diagOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/diagnose_renderer.py'),
    '--verify'
)
Add-StepResult -Name '8/10 diagnose_renderer --verify' -Ok $diagOk

# --- 9 score_institutional_render --verify (vergelijking_tabel) ---
$scoreOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/score_institutional_render.py'),
    '--verify'
)
Add-StepResult -Name '9/10 score_institutional_render --verify' -Ok $scoreOk

# --- 10 verify_pseudo_table_normalizer ---
$verifyPy = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/verify_pseudo_table_normalizer.py'
$verifyOk = Invoke-AuditCommand -Exe $python -ArgumentList @($verifyPy, '--verify')
Add-StepResult -Name '10/10 verify_pseudo_table_normalizer' -Ok $verifyOk

# --- Rapport ---
$reportFileName = 'PSEUDO_TABLE_NORMALIZER_E2E_REPORT_' + $reportStamp + '.md'
$reportPath = Join-Path $scriptRoot $reportFileName
$status = if ($failures -eq 0) { 'PASS' } else { 'FAIL' }
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Pseudo-tabel normalizer E2E - $status")
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
    [void]$sb.AppendLine("**$failures** stap(pen) gefaald. Controleer normalizer, TS parity, diagnose/score en SOUL-sync.")
} else {
    [void]$sb.AppendLine('Alle stappen geslaagd. Pseudo-tabellen worden deterministisch omgezet vóór Rich-render.')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('Runtime: na SOUL-wijziging `windows\SYNC_SOUL_SNIPPETS.bat` + `/new`.')
}
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host ''
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== PSEUDO-TABEL E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== PSEUDO-TABEL E2E: PASS ===' -ForegroundColor Green
exit 0
