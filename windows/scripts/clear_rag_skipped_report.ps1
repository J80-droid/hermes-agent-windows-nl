# Leeg het overgeslagen-rapport (vóór nieuwe N-run met gefixte OCR).
param(
    [string]$LanceDbPath = ""
)
if (-not $LanceDbPath) {
    $LanceDbPath = if ($env:HERMES_LANCEDB_PATH) { $env:HERMES_LANCEDB_PATH }
    else { Join-Path $env:USERPROFILE "data\lancedb\core" }
}
$json = Join-Path $LanceDbPath "rag_ingest_skipped_report.json"
$md = Join-Path $LanceDbPath "rag_ingest_skipped_report.md"
$empty = @{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    entries      = @()
} | ConvertTo-Json -Depth 4
Set-Content -Path $json -Value $empty -Encoding utf8
Set-Content -Path $md -Value "# RAG ingest - overgeslagen bronnen`n`n_(leeg - rapport gereset)_`n" -Encoding utf8
Write-Host "[OK] Skip-rapport geleegd: $json"
