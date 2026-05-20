# Korte E2E: temp bron + LanceDB, run_rag_ingest.ps1, live status, MCP search.
$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$e2eRoot = Join-Path $env:TEMP "hermes_rag_e2e_$stamp"
$raw = Join-Path $e2eRoot "raw"
$ldb = Join-Path $e2eRoot "lancedb"
$log = Join-Path $e2eRoot "e2e_ingest.log"
New-Item -ItemType Directory -Force -Path $raw, $ldb | Out-Null

@'
Hermes E2E testdocument. Unieke zoekterm: ZEPHYR_RAG_E2E_2026.
Dit bestand test platte UTF-8 lezen (_read_plain_utf8).
'@ | Set-Content -Path (Join-Path $raw "e2e_sample.txt") -Encoding utf8

@'
# E2E markdown
ZEPHYR_RAG_E2E_2026 staat ook in dit markdown-bestand.
'@ | Set-Content -Path (Join-Path $raw "e2e_notes.md") -Encoding utf8

# 0-byte stub-pad (verwijs-naam)
$stubPath = Join-Path $raw "DEEL 99 - E2E stub verwijzing.txt"
New-Item -ItemType File -Force -Path $stubPath | Out-Null

$env:HERMES_RAG_RAW_SOURCE = $raw
$env:HERMES_LANCEDB_PATH = $ldb
$env:HERMES_RAG_FRESH = "1"
$env:HERMES_RAG_INCREMENTAL = "0"
$env:HERMES_RAG_PERF_PROFILE = "safe"
$env:HERMES_RAG_FILE_TIMEOUT_SEC = "600"
$env:HERMES_RAG_CONVERT_TIMEOUT_SEC = "120"
$env:HERMES_RAG_LIVE_STATUS = Join-Path $ldb "rag_ingest_live_status.json"
$env:HERMES_RAG_SKIP_REPORT = Join-Path $ldb "rag_ingest_skipped_report.json"
$env:HERMES_NONINTERACTIVE = "1"

Write-Host "=== Hermes RAG E2E ===" -ForegroundColor Cyan
Write-Host "Bron: $raw"
Write-Host "DB:   $ldb"
Write-Host "Log:  $log"

$ingestScript = Join-Path $PSScriptRoot "run_rag_ingest.ps1"
& $ingestScript -LogPath $log -RepoRoot $repo
$exitIngest = $LASTEXITCODE
Write-Host "Ingest exit: $exitIngest" -ForegroundColor $(if ($exitIngest -eq 0) { "Green" } else { "Red" })

$failures = @()
if ($exitIngest -ne 0) { $failures += "ingest exit $exitIngest" }

if (-not (Test-Path $log)) { $failures += "log ontbreekt" }
else {
    $tail = Get-Content $log -Tail 30 -Encoding utf8 -ErrorAction SilentlyContinue
    if ($tail -match "\[LIVE\]") { Write-Host "[OK] [LIVE] regels in log" -ForegroundColor Green }
    else { $failures += "geen [LIVE] in log" }
    if ($tail -match "afgerond|Ingestie-scan") { Write-Host "[OK] afsluitregel in log" -ForegroundColor Green }
    else { $failures += "geen afsluitregel in log" }
}

$livePath = Join-Path $ldb "rag_ingest_live_status.json"
if (Test-Path $livePath) {
    $live = Get-Content $livePath -Raw -Encoding utf8 | ConvertFrom-Json
    Write-Host "[OK] live_status: step=$($live.step) index=$($live.current_index)/$($live.total)" -ForegroundColor Green
    if ($live.started_at -eq $live.updated_at -and $live.current_index -gt 1) {
        $failures += "started_at==updated_at bij meerdere bronnen (clock bug?)"
    }
} else {
    $failures += "live_status.json ontbreekt"
}

$verifyScript = Join-Path $e2eRoot "e2e_verify.py"
@'
import os, sys
repo = os.environ["HERMES_E2E_REPO"]
sys.path.insert(0, os.path.join(repo, "scripts", "rag_pipeline"))
os.environ.setdefault("HERMES_LANCEDB_PATH", os.environ["HERMES_E2E_LDB"])
import lancedb
from kb_schema import DB_PATH, TABLE_NAME, list_all_table_names
import mcp_server

db = lancedb.connect(DB_PATH)
names = list_all_table_names(db)
if TABLE_NAME not in names:
    print("FAIL:no_table"); raise SystemExit(2)
t = db.open_table(TABLE_NAME)
n = t.count_rows()
print(f"rows={n}")
if n < 1:
    print("FAIL:no_rows"); raise SystemExit(3)
rows = t.search("ZEPHYR_RAG_E2E_2026").limit(3).to_list()
if not rows:
    print("FAIL:no_search_hits"); raise SystemExit(4)
print("search_ok", rows[0].get("source", "?"))
mcp_server.reset_knowledge_table_cache()
out = mcp_server.search_knowledge("ZEPHYR_RAG_E2E_2026", limit=2)
if "ZEPHYR" not in out:
    print("FAIL:mcp_search"); raise SystemExit(5)
print("mcp_ok")
'@ | Set-Content -Path $verifyScript -Encoding utf8

$env:HERMES_E2E_REPO = $repo
$env:HERMES_E2E_LDB = $ldb
$activate = "$env:USERPROFILE\miniconda3\Scripts\activate.bat"
if (-not (Test-Path $activate)) { $activate = "$env:LOCALAPPDATA\miniconda3\Scripts\activate.bat" }
$verifyBat = Join-Path $env:TEMP "hermes_e2e_verify.cmd"
Set-Content $verifyBat "@echo off`ncall `"$activate`" hermes-env`ncd /d `"$repo`"`npython `"$verifyScript`"`nexit /b %ERRORLEVEL%" -Encoding ASCII
cmd /c $verifyBat
$exitVerify = $LASTEXITCODE
Remove-Item $verifyBat -Force -ErrorAction SilentlyContinue
Write-Host "Verify exit: $exitVerify" -ForegroundColor $(if ($exitVerify -eq 0) { "Green" } else { "Red" })
if ($exitVerify -ne 0) { $failures += "verify exit $exitVerify" }

# Incrementele run (moet snel skippen)
$env:HERMES_RAG_FRESH = "0"
$env:HERMES_RAG_INCREMENTAL = "1"
$log2 = Join-Path $e2eRoot "e2e_ingest_inc.log"
& $ingestScript -LogPath $log2 -RepoRoot $repo
$exitInc = $LASTEXITCODE
if ($exitInc -ne 0) { $failures += "incremental exit $exitInc" }
elseif ((Get-Content $log2 -Raw -Encoding utf8) -notmatch "ongewijzigde") {
    Write-Host "[WARN] incrementele run: geen 'ongewijzigde' melding (kan ok zijn bij 0 skip)" -ForegroundColor Yellow
} else {
    Write-Host "[OK] incrementele skip gedetecteerd" -ForegroundColor Green
}

Write-Host "`nE2E root (bewaard voor inspectie): $e2eRoot"
if ($failures.Count -gt 0) {
    Write-Host "E2E MISLUKT:" -ForegroundColor Red
    $failures | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
Write-Host "E2E GESLAAGD" -ForegroundColor Green
exit 0
