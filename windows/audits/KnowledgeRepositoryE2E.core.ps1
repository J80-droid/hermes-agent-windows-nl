# KnowledgeRepository RAG-laag E2E (architectuur, edge cases, caller wiring).
# Launcher: RUN_KNOWLEDGE_REPOSITORY_E2E.ps1
param(
    [string]$RepoRoot = '',
    [switch]$SkipPytest
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

Write-Host '=== KnowledgeRepository E2E ===' -ForegroundColor Cyan
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

# --- 1 Repo artefacten ---
$repoFiles = @(
    'scripts/rag_pipeline/knowledge_repository.py',
    'scripts/rag_pipeline/vector_store_ports.py',
    'scripts/rag_pipeline/lancedb_backend.py',
    'scripts/rag_pipeline/vector_store_lifecycle.py',
    'scripts/rag_pipeline/kb_schema.py',
    'scripts/rag_pipeline/mcp_server.py',
    'scripts/rag_pipeline/ingest.py',
    'scripts/rag_pipeline/lancedb_maintenance.py',
    'tests/rag_pipeline/test_knowledge_repository.py'
)
$artOk = $true
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $artOk = $false
        break
    }
}
Add-StepResult -Name '1/8 repo KnowledgeRepository artefacten' -Ok $artOk

# --- 2 KnowledgeRepository edge-case API ---
$repoPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/knowledge_repository.py')
$apiOk = ($repoPy -match 'if not str\(query\)\.strip\(\)') -and
    ($repoPy -match "upsert_chunks requires each row to include an 'id' key") -and
    ($repoPy -match 'merge_insert failed') -and
    ($repoPy -match 'Callable\[\[\], None\]')
Add-StepResult -Name '2/8 KnowledgeRepository edge-case API' -Ok $apiOk

# --- 3 MCP shutdown via backend (geen repo-singleton bij import) ---
$mcpPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/mcp_server.py')
$mcpOk = ($mcpPy -match 'get_vector_store_backend\(\)\.register_shutdown_hooks') -and
    ($mcpPy -notmatch '_get_repo\(\)\.register_shutdown_hooks')
Add-StepResult -Name '3/8 MCP shutdown hooks op VectorStoreBackend' -Ok $mcpOk

# --- 4 Ingest repo threading ---
$ingestPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/ingest.py')
$ingestOk = ($ingestPy -match '_upsert_chunk_rows\(table, rows, repo=repo\)') -and
    ($ingestPy -match 'repo=repo')
Add-StepResult -Name '4/8 ingest upsert gebruikt gedeelde repo' -Ok $ingestOk

# --- 5 Isolated harness (8 scenario''s) ---
$harness = Join-Path $scriptRoot 'KnowledgeRepositoryE2E.harness.py'
$harnessOk = Invoke-AuditCommand -Exe $python -ArgumentList @($harness)
Add-StepResult -Name '5/8 isolated harness (8 scenario''s)' -Ok $harnessOk

# --- 6 Pytest knowledge_repository ---
if ($SkipPytest) {
    Add-StepResult -Name '6/8 pytest test_knowledge_repository' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $pytestOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/rag_pipeline/test_knowledge_repository.py'),
        '-q', '--tb=short', '-o', 'addopts='
    )
    Add-StepResult -Name '6/8 pytest test_knowledge_repository' -Ok $pytestOk -Detail $python
}

# --- 7 lancedb_maintenance session via repository ---
$maintPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/lancedb_maintenance.py')
$maintOk = ($maintPy -match 'KnowledgeRepository') -and
    ($maintPy -match '\.session\(\)') -and
    ($maintPy -notmatch '^import lancedb\b')
Add-StepResult -Name '7/8 lancedb_maintenance lazy session via repository' -Ok $maintOk

# --- 8 Footguns RAG modules ---
$footguns = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/check-windows-footguns.py'
$fgOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
    $footguns,
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/knowledge_repository.py'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/mcp_server.py'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/ingest.py'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/lancedb_maintenance.py')
)
Add-StepResult -Name '8/8 windows footguns (RAG callers)' -Ok $fgOk

# --- Rapport ---
$status = if ($failures -eq 0) { 'PASS' } else { "FAIL ($failures)" }
$reportFileName = 'KNOWLEDGE_REPOSITORY_E2E_REPORT_' + $reportStamp + '.md'
$reportPath = Join-Path $scriptRoot $reportFileName
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# KnowledgeRepository E2E - $status")
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
[void]$sb.AppendLine('- KnowledgeRepository session/search/upsert/ensure_table')
[void]$sb.AppendLine('- Edge cases: empty search, invalid limit, missing id, merge_insert wrap')
[void]$sb.AppendLine('- MCP shutdown via get_vector_store_backend; ingest repo threading')
[void]$sb.AppendLine('- lancedb_maintenance lazy KnowledgeRepository.session')
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== KNOWLEDGE REPOSITORY E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== KNOWLEDGE REPOSITORY E2E: PASS ===' -ForegroundColor Green
exit 0
