# Performance + architecture refactor E2E (RAG lifecycle, scan, MCP, config, runtime).
# Launcher: RUN_PERFORMANCE_ARCHITECTURE_E2E.ps1
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

Write-Host '=== Performance Architecture E2E ===' -ForegroundColor Cyan
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

# --- 1 Repo artefacten ---
$repoFiles = @(
    'scripts/rag_pipeline/ingest_chunking.py',
    'scripts/rag_pipeline/document_converter.py',
    'scripts/rag_pipeline/bootstrap_ingest_state.py',
    'scripts/rag_pipeline/schema_migrate.py',
    'scripts/rag_pipeline/source_formats.py',
    'scripts/rag_pipeline/orphan_cleanup.py',
    'hermes_cli/config_snapshot.py',
    'agent/review_snapshot.py',
    'windows/audits/PerformanceArchitectureE2E.harness.py'
)
$artOk = $true
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $artOk = $false
        break
    }
}
Add-StepResult -Name '1/10 repo performance-architecture artefacten' -Ok $artOk

# --- 2 LanceDB lifecycle utilities ---
$schemaPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/schema_migrate.py')
$bootPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/bootstrap_ingest_state.py')
$lifeOk = ($schemaPy -match 'KnowledgeRepository') -and
    ($schemaPy -match '\.session\(\)') -and
    ($schemaPy -notmatch 'lancedb\.connect') -and
    ($bootPy -match 'KnowledgeRepository') -and
    ($bootPy -match '_resolve_source_file') -and
    ($bootPy -match 'dataset\.scan\(columns=\["source"\]')
Add-StepResult -Name '2/10 LanceDB lifecycle + bootstrap source scan' -Ok $lifeOk

# --- 3 Ingest scan + module split ---
$sfPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/source_formats.py')
$ingestPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/ingest.py')
$scanOk = ($sfPy -match 'def collect_indexed_files') -and
    ($sfPy -match 'os\.scandir') -and
    ($ingestPy -match 'collect_indexed_files') -and
    ($ingestPy -match 'from ingest_chunking import') -and
    ($ingestPy -match 'from document_converter import') -and
    ($ingestPy -notmatch 'for ext in extensions')
Add-StepResult -Name '3/10 single tree scan + ingest split imports' -Ok $scanOk

# --- 4 MCP unified connect ---
$mcpPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/mcp_server.py')
$mcpOk = ($mcpPy -match 'def _ensure_mcp_knowledge') -and
    ($mcpPy -match 'close_lancedb_mcp_connection\(\)') -and
    ($mcpPy -match 'repo\.search\(query') -and
    ($mcpPy -notmatch 'def _get_knowledge_table')
Add-StepResult -Name '4/10 MCP _ensure_mcp_knowledge + search via repo' -Ok $mcpOk

# --- 5 Ingest state fingerprint + handlers ---
$statePy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/ingest_state.py')
$handPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/ingest_handlers.py')
$ingOptOk = ($statePy -match 'tuple\[bool, str \| None\]') -and
    ($statePy -match 'content_hash') -and
    ($ingestPy -match 'fingerprint_by_rel') -and
    ($handPy -match 'get_markitdown_converter') -and
    ($handPy -notmatch 'ThreadPoolExecutor')
Add-StepResult -Name '5/10 ingest fingerprint + shared MarkItDown' -Ok $ingOptOk

# --- 6 Config snapshot + gateway cache ---
$cfgSnap = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'hermes_cli/config_snapshot.py')
$gwCfg = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'gateway/config.py')
$sandboxPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'hermes_cli/filesystem_sandbox.py')
$cfgOk = ($cfgSnap -match 'class ConfigSnapshot') -and
    ($cfgSnap -match 'get_config_snapshot') -and
    ($gwCfg -match '_gw_config_cache') -and
    ($gwCfg -match 'bust_gateway_config_cache') -and
    ($sandboxPy -match '_SANDBOX_CONFIG_MTIME_NS') -and
    ($sandboxPy -match 'get_config_snapshot')
Add-StepResult -Name '6/10 config snapshot + gateway/sandbox cache' -Ok $cfgOk

# --- 7 Runtime hygiene ---
$procPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tools/process_registry.py')
$mcpTool = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tools/mcp_tool.py')
$hwPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'hermes_cli/hardware_backend.py')
$rtOk = ($procPy -match '_release_local_popen_io') -and
    ($procPy -match 'completion_queue.*maxsize=256') -and
    ($procPy -match '_enqueue_completion_event') -and
    ($mcpTool -match '_mcp_stderr_log_fh = None') -and
    ($hwPy -match '_whisper_model_cache') -and
    ($hwPy -match 'clear_faster_whisper_model_cache')
Add-StepResult -Name '7/10 process/MCP stderr/whisper cache wiring' -Ok $rtOk

# --- 8 py_compile kernmodules ---
$compileList = @(
    'scripts/rag_pipeline/ingest.py',
    'scripts/rag_pipeline/bootstrap_ingest_state.py',
    'scripts/rag_pipeline/schema_migrate.py',
    'scripts/rag_pipeline/mcp_server.py',
    'hermes_cli/config_snapshot.py',
    'windows/audits/PerformanceArchitectureE2E.harness.py'
)
$compileOk = $true
foreach ($rel in $compileList) {
    $full = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel
    if (-not (Invoke-AuditCommand -Exe $python -ArgumentList @('-m', 'py_compile', $full))) {
        $compileOk = $false
        break
    }
}
Add-StepResult -Name '8/10 py_compile kernmodules' -Ok $compileOk -Detail $python

# --- 9 Isolated harness (11 scenario''s) ---
$harness = Join-Path $scriptRoot 'PerformanceArchitectureE2E.harness.py'
$harnessOk = Invoke-AuditCommand -Exe $python -ArgumentList @($harness)
Add-StepResult -Name '9/10 isolated harness (11 scenario''s)' -Ok $harnessOk

# --- 10 Pytest subset ---
if ($SkipPytest) {
    Add-StepResult -Name '10/10 pytest performance-architecture subset' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $pytestPaths = @(
        'tests/rag_pipeline/test_knowledge_repository.py',
        'tests/rag_pipeline/test_vector_store_ports.py',
        'tests/rag_pipeline/test_lancedb_storage.py',
        'tests/rag_pipeline/test_bootstrap_ingest_state.py',
        'tests/rag_pipeline/test_ingest_chunking.py',
        'tests/rag_pipeline/test_orphan_cleanup.py',
        'tests/rag_pipeline/test_source_formats.py',
        'tests/rag_pipeline/test_document_converter.py',
        'tests/rag_pipeline/test_ingest_state_needs_processing.py',
        'tests/rag_pipeline/test_mcp_server.py',
        'tests/hermes_cli/test_config_snapshot.py',
        'tests/agent/test_review_snapshot.py',
        'tests/hermes_cli/test_filesystem_sandbox.py',
        'tests/hermes_cli/test_hardware_backend.py',
        'tests/tools/test_process_registry.py'
    )
    $pytestOk = $true
    foreach ($rel in $pytestPaths) {
        if (-not (Invoke-AuditCommand -Exe $python -ArgumentList @(
                '-m', 'pytest',
                (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel),
                '-q', '--tb=short', '-o', 'addopts='
            ))) {
            $pytestOk = $false
            break
        }
    }
    Add-StepResult -Name '10/10 pytest performance-architecture subset' -Ok $pytestOk -Detail $python
}

# --- Rapport ---
$status = if ($failures -eq 0) { 'PASS' } else { "FAIL ($failures)" }
$reportFileName = 'PERFORMANCE_ARCHITECTURE_E2E_REPORT_' + $reportStamp + '.md'
$reportPath = Join-Path $scriptRoot $reportFileName
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Performance Architecture E2E - $status")
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
[void]$sb.AppendLine('- LanceDB lifecycle (schema_migrate, bootstrap) via KnowledgeRepository')
[void]$sb.AppendLine('- Single directory scan (collect_indexed_files)')
[void]$sb.AppendLine('- MCP unified connect; ingest fingerprint + shared MarkItDown')
[void]$sb.AppendLine('- Config snapshot; gateway cache; sandbox mtime bust')
[void]$sb.AppendLine('- Process registry pipes; MCP stderr close; Whisper model cache')
[void]$sb.AppendLine('- ingest_chunking + document_converter modules')
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== PERFORMANCE ARCHITECTURE E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== PERFORMANCE ARCHITECTURE E2E: PASS ===' -ForegroundColor Green
exit 0
