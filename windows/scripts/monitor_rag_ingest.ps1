# Eén regel status voor lopende productie-ingest (live JSON + proces).
param([string]$LivePath = "$env:USERPROFILE\data\my_lancedb\rag_ingest_live_status.json")

if (-not (Test-Path $LivePath)) {
    Write-Host "[MONITOR] Geen live status: $LivePath (ingest nog niet in index-fase?)"
    exit 2
}
$live = Get-Content $LivePath -Raw -Encoding utf8 | ConvertFrom-Json
$py = Get-Process -Id $live.pid -ErrorAction SilentlyContinue
$short = ($live.relative_source -replace '\\', '/') -split '/' | Select-Object -Last 1
Write-Host "[MONITOR] $($live.current_index)/$($live.total) | $($live.step) | $short"
Write-Host "          $($live.extra)"
Write-Host "          updated: $($live.updated_at)"
if ($py) {
    Write-Host "          pid $($live.pid) CPU $([math]::Round($py.CPU,1))s RAM $([math]::Round($py.WorkingSet64/1MB)) MB"
} else {
    Write-Host "          pid $($live.pid) niet actief (klaar of gecrasht?)"
    exit 1
}
exit 0
