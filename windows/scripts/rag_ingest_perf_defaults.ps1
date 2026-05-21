# Institutional RAG ingest performance defaults (override-friendly).
# Called from update_knowledge.bat: use -EmitCmd so SET lines apply in the parent CMD session.
# See scripts/rag_pipeline/ACTIVATION.md and windows/INSTITUTIONAL.md.
param(
    [switch]$EmitCmd
)

function Get-RagPerfDefault {
    # Institutioneel default: safe (sequentieel, lage RAM, timeouts via update_knowledge.bat)
    $perfProfile = if ($env:HERMES_RAG_PERF_PROFILE) { $env:HERMES_RAG_PERF_PROFILE.Trim().ToLowerInvariant() } else { 'safe' }

    $cpu = [Environment]::ProcessorCount
    if ($cpu -lt 1) { $cpu = 4 }

    $workers = $null
    $embedBatch = $null
    $heartbeat = $null

    switch ($perfProfile) {
        'safe' {
            $workers = 2
            $embedBatch = 32
            $heartbeat = 5
        }
        'fast' {
            $workers = [Math]::Min($cpu, 8)
            $embedBatch = 128
            $heartbeat = 2
        }
        'off' {
            return @{
                Profile   = 'off'
                Cpu       = $cpu
                Workers   = $env:HERMES_RAG_CONVERT_WORKERS
                EmbedBatch = $env:HERMES_RAG_EMBED_BATCH
                Heartbeat = $env:HERMES_RAG_CONVERT_HEARTBEAT_SEC
            }
        }
        'balanced' {
            $half = [Math]::Floor($cpu / 2)
            $workers = [Math]::Min([Math]::Max($half, 2), 8)
            $embedBatch = 64
            $heartbeat = 3
        }
        default {
            Write-Host "[WARN] Unknown HERMES_RAG_PERF_PROFILE='$perfProfile'; using balanced"
            $perfProfile = 'balanced'
            $half = [Math]::Floor($cpu / 2)
            $workers = [Math]::Min([Math]::Max($half, 2), 8)
            $embedBatch = 64
            $heartbeat = 3
        }
    }

    if ($perfProfile -ne 'off') {
        if (-not $env:HERMES_RAG_CONVERT_WORKERS) {
            $env:HERMES_RAG_CONVERT_WORKERS = [string]$workers
        }
        if (-not $env:HERMES_RAG_EMBED_BATCH) {
            $env:HERMES_RAG_EMBED_BATCH = [string]$embedBatch
        }
        if (-not $env:HERMES_RAG_CONVERT_HEARTBEAT_SEC) {
            $env:HERMES_RAG_CONVERT_HEARTBEAT_SEC = [string]$heartbeat
        }
    }

    return @{
        Profile    = $perfProfile
        Cpu        = $cpu
        Workers    = $env:HERMES_RAG_CONVERT_WORKERS
        EmbedBatch = $env:HERMES_RAG_EMBED_BATCH
        Heartbeat  = $env:HERMES_RAG_CONVERT_HEARTBEAT_SEC
    }
}

$vals = Get-RagPerfDefault

if ($vals.Profile -eq 'off') {
    $msg = '[INFO] RAG perf profile=off (ingest.py defaults; set HERMES_RAG_PERF_PROFILE or explicit env to override)'
    if ($EmitCmd) { Write-Output "echo $msg" } else { Write-Host $msg }
    exit 0
}

$info = "[INFO] RAG perf profile=$($vals.Profile) workers=$($vals.Workers) embed_batch=$($vals.EmbedBatch) heartbeat=$($vals.Heartbeat)s (CPU=$($vals.Cpu); explicit env vars win)"

if ($EmitCmd) {
    # Parent CMD: for /f %%L in ('powershell ... -EmitCmd') do %%L
    Write-Output "echo $info"
    if ($vals.Workers) { Write-Output "set HERMES_RAG_CONVERT_WORKERS=$($vals.Workers)" }
    if ($vals.EmbedBatch) { Write-Output "set HERMES_RAG_EMBED_BATCH=$($vals.EmbedBatch)" }
    if ($vals.Heartbeat) { Write-Output "set HERMES_RAG_CONVERT_HEARTBEAT_SEC=$($vals.Heartbeat)" }
    if (-not $env:HERMES_RAG_ALLOW_PARALLEL) { Write-Output "set HERMES_RAG_ALLOW_PARALLEL=0" }
    if (-not $env:HERMES_RAG_FILE_TIMEOUT_SEC) { Write-Output "set HERMES_RAG_FILE_TIMEOUT_SEC=1200" }
    if (-not $env:HERMES_RAG_CONVERT_TIMEOUT_SEC) { Write-Output "set HERMES_RAG_CONVERT_TIMEOUT_SEC=300" }
    if (-not $env:HERMES_RAG_STATE_CHECKPOINT) { Write-Output "set HERMES_RAG_STATE_CHECKPOINT=25" }
    if (-not $env:HERMES_RAG_MAX_CHUNKS_PER_SOURCE) { Write-Output "set HERMES_RAG_MAX_CHUNKS_PER_SOURCE=800" }
    if (-not $env:HERMES_RAG_LIVE_TICK_SEC) { Write-Output "set HERMES_RAG_LIVE_TICK_SEC=3" }
    if (-not $env:HERMES_RAG_LIVE_LOG) { Write-Output "set HERMES_RAG_LIVE_LOG=1" }
    if (-not $env:HERMES_RAG_SKIP_WHISPER_WITHOUT_SIDECAR) { Write-Output "set HERMES_RAG_SKIP_WHISPER_WITHOUT_SIDECAR=1" }
    if (-not $env:HERMES_RAG_PREFER_SIDECAR) { Write-Output "set HERMES_RAG_PREFER_SIDECAR=1" }
} else {
    Write-Host $info
}

exit 0
