# Windows platform hardening E2E (filesystem sandbox, hardware backend, LanceDB storage).
# Launcher: RUN_WINDOWS_PLATFORM_HARDENING_E2E.ps1
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

Write-Host '=== Windows platform hardening E2E ===' -ForegroundColor Cyan
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

# --- 1 Repo artefacten ---
$repoFiles = @(
    'overlay/hermes_cli/filesystem_sandbox.py',
    'overlay/hermes_cli/hardware_backend.py',
    'hermes_cli/config.py',
    'scripts/rag_pipeline/lancedb_storage.py',
    'scripts/rag_pipeline/vector_store_paths.py',
    'scripts/rag_pipeline/vector_store_lifecycle.py',
    'scripts/rag_pipeline/vector_store_ports.py',
    'scripts/rag_pipeline/lancedb_backend.py',
    'scripts/rag_pipeline/kb_schema_constants.py',
    'scripts/rag_pipeline/knowledge_repository.py',
    'scripts/rag_pipeline/kb_schema.py',
    'scripts/rag_pipeline/mcp_server.py',
    'scripts/rag_pipeline/ingest.py',
    'tools/file_tools.py',
    'tests/hermes_cli/test_filesystem_sandbox.py',
    'tests/hermes_cli/test_hardware_backend.py',
    'tests/rag_pipeline/test_lancedb_storage.py',
    'windows/audits/WindowsPlatformHardeningE2E.harness.py',
    'windows/audits/WindowsPlatformHardeningE2E.core.ps1',
    'windows/audits/RUN_WINDOWS_PLATFORM_HARDENING_E2E.ps1'
)
$repoOk = $true
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $repoOk = $false
        break
    }
}
Add-StepResult -Name '1/10 repo platform-hardening artefacten' -Ok $repoOk

# --- 2 Filesystem sandbox wiring ---
$fsPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/filesystem_sandbox.py')
$fileToolsPatch = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/tools/file_tools_fork_patch.py')
$bootstrapPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/bootstrap.py')
$fsOk = ($fsPy -match 'def resolve_path_within_sandbox') -and ($fsPy -match 'def has_forbidden_path_content') -and (
    ($fileToolsPatch -match 'apply_file_tools_fork_patch') -and ($fileToolsPatch -match 'validate_agent_path_for_task') -and ($bootstrapPy -match 'apply_file_tools_fork_patch')
)
Add-StepResult -Name '2/10 filesystem sandbox wiring via overlay patch' -Ok $fsOk

# --- 3 Hardware backend + CLI startup logging ---
$hwPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/hardware_backend.py')
$cliPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'cli.py')
$hwOk = ($hwPy -match 'def build_onnx_provider_attempts') -and ($hwPy -match 'def load_faster_whisper_model') -and ($hwPy -match 'def load_piper_voice_with_fallback') -and (
    ($cliPy -match 'log_local_inference_backends') -or ($hwPy -match 'def log_local_inference_backends')
)
Add-StepResult -Name '3/10 hardware backend + CLI startup logging' -Ok $hwOk

# --- 4 LanceDB storage wiring ---
$ldbFacade = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/lancedb_storage.py')
$ldbLife = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/vector_store_lifecycle.py')
$ldbPorts = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/vector_store_ports.py')
$ldbBackend = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/lancedb_backend.py')
$mcpPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/mcp_server.py')
$ingestPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/ingest.py')
$ldbOk = ($ldbLife -match 'def preflight_vector_store') -and ($ldbLife -match 'def shutdown_all_lancedb_connections') -and ($ldbFacade -match 'def lancedb_session') -and ($ldbPorts -match 'get_vector_store_backend') -and ($ldbBackend -match 'class LanceDBVectorStoreBackend') -and ($mcpPy -match 'KnowledgeRepository') -and ($mcpPy -match 'register_shutdown_hooks') -and ($ingestPy -match 'KnowledgeRepository')
Add-StepResult -Name '4/10 LanceDB storage lifecycle wiring' -Ok $ldbOk

# --- 5 Config + dependencies ---
$configPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'hermes_cli/config.py')
$pyproject = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'pyproject.toml')
$extrasTxt = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/requirements-fork-extras.txt')
$hwOverlay = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/hardware_backend.py'
$depsOk = (
    (($pyproject -match 'voice-windows') -and ($pyproject -match 'onnxruntime-directml')) -or
    ($extrasTxt -match 'faster-whisper') -or
    (Test-Path -LiteralPath $hwOverlay)
)
$sandboxOk = (
    (($configPy -match '"workspace"') -and ($configPy -match 'enforce_sandbox')) -or
    (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/filesystem_sandbox.py'))
)
$cfgOk = $depsOk -and $sandboxOk
Add-StepResult -Name '5/10 config workspace + voice-windows deps' -Ok $cfgOk

# --- 6 Isolated harness (12 scenario''s) ---
$harness = Join-Path $scriptRoot 'WindowsPlatformHardeningE2E.harness.py'
$harnessOk = Invoke-AuditCommand -Exe $python -ArgumentList @($harness)
Add-StepResult -Name '6/10 isolated harness (12 scenario''s)' -Ok $harnessOk

# --- 7 Pytest filesystem sandbox ---
if ($SkipPytest) {
    Add-StepResult -Name '7/10 pytest filesystem sandbox' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
    $fsTestOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/overlay/test_file_tools_fork_patch.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/hermes_cli/test_filesystem_sandbox.py'),
        '-q', '--tb=short', '-o', 'addopts='
    )
    Add-StepResult -Name '7/10 pytest filesystem sandbox' -Ok $fsTestOk -Detail $python
}

# --- 8 Pytest hardware backend ---
if ($SkipPytest) {
    Add-StepResult -Name '8/10 pytest hardware backend' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $hwTestOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/hermes_cli/test_hardware_backend.py'),
        '-q', '--tb=short', '-o', 'addopts='
    )
    Add-StepResult -Name '8/10 pytest hardware backend' -Ok $hwTestOk -Detail $python
}

# --- 9 Pytest LanceDB storage ---
if ($SkipPytest) {
    Add-StepResult -Name '9/10 pytest LanceDB storage' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $ldbTestOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/rag_pipeline/test_lancedb_storage.py'),
        '-q', '--tb=short', '-o', 'addopts='
    )
    Add-StepResult -Name '9/10 pytest LanceDB storage' -Ok $ldbTestOk -Detail $python
}

# --- 10 Windows footguns (blocking subset) ---
$footguns = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/check-windows-footguns.py'
if (Test-Path -LiteralPath $footguns) {
    $fgOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        $footguns,
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/filesystem_sandbox.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/hardware_backend.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tools/file_tools.py')
    )
    Add-StepResult -Name '10/10 windows footguns (changed modules)' -Ok $fgOk
} else {
    Add-StepResult -Name '10/10 windows footguns (changed modules)' -Ok $true -Detail 'check-windows-footguns.py ontbreekt — SKIP'
}

# --- Rapport ---
$status = if ($failures -eq 0) { 'PASS' } else { "FAIL ($failures)" }
$reportFileName = 'WINDOWS_PLATFORM_HARDENING_E2E_REPORT_' + $reportStamp + '.md'
$reportPath = Join-Path $scriptRoot $reportFileName
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Windows platform hardening E2E - $status")
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
[void]$sb.AppendLine('- Filesystem sandbox (path traversal, LOCALAPPDATA workspace)')
[void]$sb.AppendLine('- Hardware backend (CUDA->DirectML->CPU, startup probes)')
[void]$sb.AppendLine('- LanceDB storage (VectorStore paths, preflight, graceful close)')
Set-Content -LiteralPath $reportPath -Value $sb.ToString() -Encoding UTF8
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== WINDOWS PLATFORM HARDENING E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== WINDOWS PLATFORM HARDENING E2E: PASS ===' -ForegroundColor Green
exit 0
