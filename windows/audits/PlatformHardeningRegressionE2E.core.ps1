# Platform hardening regression E2E (code-review fixes, PS1 path convention, footguns).
# Launcher: RUN_PLATFORM_HARDENING_REGRESSION_E2E.ps1
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

Write-Host '=== Platform hardening regression E2E ===' -ForegroundColor Cyan
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$python = Get-HermesAuditPython
$env:PYTHONPATH = $RepoRoot

# --- 1 Repo artefacten ---
$repoFiles = @(
    'overlay/hermes_cli/filesystem_sandbox.py',
    'overlay/hermes_cli/hardware_backend.py',
    'scripts/rag_pipeline/lancedb_storage.py',
    'scripts/rag_pipeline/vector_store_paths.py',
    'scripts/rag_pipeline/vector_store_lifecycle.py',
    'scripts/rag_pipeline/vector_store_ports.py',
    'scripts/rag_pipeline/lancedb_backend.py',
    'scripts/rag_pipeline/kb_schema_constants.py',
    'scripts/rag_pipeline/knowledge_repository.py',
    'tools/file_tools.py',
    'tools/terminal_tool.py',
    'scripts/check-windows-footguns.py',
    'windows/HermesShellCommon.ps1',
    'windows/audits/PlatformHardeningRegressionE2E.harness.py',
    'windows/audits/PlatformHardeningRegressionE2E.core.ps1',
    'windows/audits/RUN_PLATFORM_HARDENING_REGRESSION_E2E.ps1'
)
$repoOk = $true
foreach ($rel in $repoFiles) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $repoOk = $false
        break
    }
}
Add-StepResult -Name '1/10 repo regression artefacten' -Ok $repoOk

# --- 2 Geen legacy PS1 pad-patroon in audits ---
$legacyPattern = "-replace\s+'/',\s+'\\\\'"
$auditDir = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/audits'
$legacyHits = @()
Get-ChildItem -LiteralPath $auditDir -Filter '*.ps1' -File | ForEach-Object {
    $text = Read-HermesRepoText -Path $_.FullName
    if ($text -match $legacyPattern) {
        $legacyHits += $_.Name
    }
}
Add-StepResult -Name '2/10 audits: geen legacy `$rel -replace` pad-patroon' -Ok ($legacyHits.Count -eq 0) -Detail ($legacyHits -join ', ')

# --- 3 Join-HermesRepoPath conventie in HermesShellCommon ---
$commonPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/HermesShellCommon.ps1')
$commonOk = ($commonPy -match 'function Join-HermesRepoPath') -and
    ($commonPy -match 'Read-HermesRepoText') -and
    ($commonPy -match 'Navigatie t.o.v. het script')
Add-StepResult -Name '3/10 HermesShellCommon pad-conventie gedocumenteerd' -Ok $commonOk

# --- 4 Footguns PS1 pad-regel ---
$footgunsPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/check-windows-footguns.py')
$footOk = ($footgunsPy -match 'PS1: legacy Join-Path with -replace') -and
    ($footgunsPy -match 'windows" in path.parts')
Add-StepResult -Name '4/10 check-windows-footguns PS1 pad-regel' -Ok $footOk

# --- 5 Code wiring (review fixes) ---
$fsPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/filesystem_sandbox.py')
$hwPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/hardware_backend.py')
$ldbLife = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/vector_store_lifecycle.py')
$ldbPorts = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/vector_store_ports.py')
$ldbBackend = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/lancedb_backend.py')
$fileTools = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tools/file_tools.py')
$wireOk = ($fsPy -match 'os\.path\.expandvars') -and
    ($hwPy -match 'GPU fallback') -and
    ($ldbLife -match '_run_shutdown_hooks') -and
    ($ldbLife -match '_extra_shutdown') -and
    ($ldbPorts -match 'VectorStoreBackend') -and
    ($ldbBackend -match 'LanceDBVectorStoreBackend') -and
    ($fileTools -match 'except PermissionError')
Add-StepResult -Name '5/10 code wiring review-fixes' -Ok $wireOk

# --- 6 Isolated harness (10 scenario''s) ---
$harness = Join-Path $scriptRoot 'PlatformHardeningRegressionE2E.harness.py'
$harnessOk = Invoke-AuditCommand -Exe $python -ArgumentList @($harness)
Add-StepResult -Name '6/10 isolated harness (10 scenario''s)' -Ok $harnessOk

# --- 7 Pytest regressie-subset ---
if ($SkipPytest) {
    Add-StepResult -Name '7/10 pytest regressie-subset' -Ok $true -Detail 'overgeslagen (-SkipPytest)'
} else {
    $pytestOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
        '-m', 'pytest',
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/hermes_cli/test_filesystem_sandbox.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/hermes_cli/test_hardware_backend.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/rag_pipeline/test_lancedb_storage.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/rag_pipeline/test_vector_store_ports.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/rag_pipeline/test_kb_schema_lazy.py'),
        (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tests/rag_pipeline/test_knowledge_repository.py'),
        '-q', '--tb=short', '-o', 'addopts='
    )
    Add-StepResult -Name '7/10 pytest regressie-subset' -Ok $pytestOk -Detail $python
}

# --- 8 Footguns scan changed modules ---
$footguns = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/check-windows-footguns.py'
$fgOk = Invoke-AuditCommand -Exe $python -ArgumentList @(
    $footguns,
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/filesystem_sandbox.py'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'overlay/hermes_cli/hardware_backend.py'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'tools/file_tools.py'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/lancedb_storage.py'),
    (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/knowledge_repository.py')
)
Add-StepResult -Name '8/10 windows footguns (changed modules)' -Ok $fgOk

# --- 9 Architecture modules ---
$archFiles = @(
    'scripts/rag_pipeline/knowledge_repository.py',
    'scripts/rag_pipeline/vector_store_ports.py',
    'scripts/rag_pipeline/lancedb_backend.py',
    'scripts/rag_pipeline/kb_schema_constants.py'
)
$archOk = $true
foreach ($rel in $archFiles) {
    if (-not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel))) {
        $archOk = $false
        break
    }
}
$repoPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/knowledge_repository.py')
$archOk = $archOk -and ($repoPy -match 'class KnowledgeRepository') -and ($repoPy -match 'def ensure_table')
Add-StepResult -Name '9/10 KnowledgeRepository + VectorStore DI modules' -Ok $archOk

# --- 10 MCP + ingest use repository layer ---
$mcpPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/mcp_server.py')
$ingestPy = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/rag_pipeline/ingest.py')
$callerOk = ($mcpPy -match 'KnowledgeRepository') -and ($ingestPy -match 'KnowledgeRepository')
Add-StepResult -Name '10/10 ingest + MCP wired via KnowledgeRepository' -Ok $callerOk

# --- Rapport ---
$status = if ($failures -eq 0) { 'PASS' } else { "FAIL ($failures)" }
$reportFileName = 'PLATFORM_HARDENING_REGRESSION_E2E_REPORT_' + $reportStamp + '.md'
$reportPath = Join-Path $scriptRoot $reportFileName
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Platform hardening regression E2E - $status")
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
[void]$sb.AppendLine('- Sandbox env-var traversal + case-insensitive device paths')
[void]$sb.AppendLine('- Hardware CUDA/auto CPU fallback + patch_tool sandbox block')
[void]$sb.AppendLine('- LanceDB unified shutdown hooks (_extra_shutdown) + KnowledgeRepository')
[void]$sb.AppendLine('- PS1 Join-HermesRepoPath convention (no legacy -replace in audits)')
[void]$sb.AppendLine('- check-windows-footguns PS1 path enforcement')
[void]$sb.AppendLine('- Runtime: PermissionError propagation + repository DI harness')
Set-Content -LiteralPath $reportPath -Value $sb.ToString() -Encoding UTF8
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== PLATFORM HARDENING REGRESSION E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== PLATFORM HARDENING REGRESSION E2E: PASS ===' -ForegroundColor Green
exit 0
