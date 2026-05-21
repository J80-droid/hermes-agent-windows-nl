param(
    [string]$Domain = "legal"
)

$ldb = Join-Path $env:USERPROFILE "data\lancedb\$Domain"
$summary = Join-Path $ldb "rag_ingest_run_summary.json"
$state = Join-Path $ldb ".hermes_rag_ingest_state.json"

if (-not $env:HERMES_REPO) {
    if (Test-Path (Join-Path $env:USERPROFILE "data\hermes_agent_repo.txt")) {
        $env:HERMES_REPO = (Get-Content (Join-Path $env:USERPROFILE "data\hermes_agent_repo.txt") -Raw).Trim()
    } else {
        $env:HERMES_REPO = "D:\A.I\APPS\Hermes_agent_WS\hermes-agent"
    }
}

$py = Join-Path $env:USERPROFILE "miniconda3\envs\hermes-env\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Write-Host ""
Write-Host "[INFO] Hermes RAG ingest status - domein: $Domain"
Write-Host "================================================"
Write-Host "Tijd: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "Map:  $ldb"
Write-Host ""

if (Test-Path (Join-Path $ldb "knowledge_base.lance")) {
    Write-Host "[OK] LanceDB-tabel knowledge_base.lance aanwezig"
} else {
    Write-Host "[WARN] knowledge_base.lance nog niet gevonden"
}

if (Test-Path $state) {
    $t = (Get-Item $state).LastWriteTime
    Write-Host "[OK] ingest state - laatst gewijzigd: $t"
} else {
    Write-Host "[WARN] Geen .hermes_rag_ingest_state.json"
}

Write-Host ""
if (Test-Path $summary) {
    Write-Host "[OK] Eindrapport: rag_ingest_run_summary.json"
    $s = Get-Content -LiteralPath $summary -Raw | ConvertFrom-Json
    Write-Host "  gegenereerd:       $($s.generated_at)"
    Write-Host "  scan totaal:       $($s.scan_total_files)"
    Write-Host "  in index state:    $($s.total_sources_in_index_state)"
    Write-Host "  geindexeerd run:   $($s.indexed_this_run)"
    Write-Host "  skips totaal:      $($s.skipped_total)"
    Write-Host "  alles geindexeerd: $($s.all_sources_indexed)"
} else {
    Write-Host "[WARN] Geen rag_ingest_run_summary.json"
}

Write-Host ""
$liveCli = Join-Path $env:HERMES_REPO "scripts\rag_pipeline\ingest_live_status.py"
if (Test-Path $liveCli) {
    $liveJson = & $py $liveCli --db-path $ldb --reconcile --json 2>$null | Out-String
    $liveReport = $liveJson.Trim() | ConvertFrom-Json
    if ($liveReport) {
        $tag = switch ($liveReport.display_state) {
            'running' { '[INFO]' }
            'completed' { '[OK]' }
            'failed' { '[ERROR]' }
            default { '[WARN]' }
        }
        if ($liveReport.reconciled) {
            Write-Host "[OK] live_status gesynchroniseerd met eindrapport"
        }
        Write-Host "$tag Live: $($liveReport.human)"
        if ($liveReport.display_state -eq 'running' -and $liveReport.pid_alive) {
            Write-Host "      (ingest is NU bezig - niet Kanban/parallelle ingest op deze DB)"
        }
    }
} elseif (Test-Path (Join-Path $ldb "rag_ingest_live_status.json")) {
    Write-Host "[WARN] live_status aanwezig maar CLI ontbreekt - update hermes-agent repo"
} else {
    Write-Host "[INFO] Geen live_status"
}

Write-Host ""
Write-Host "Volgende stappen:"
Write-Host "  1. Rooktest:  hermes -p $Domain"
Write-Host "  2. Ingest:    update_knowledge.bat $Domain"
Write-Host ('  3. MCP:       update_knowledge.bat ' + '--mcp-test')
