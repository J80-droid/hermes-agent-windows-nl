# Institutional RAG ingest performance defaults (override-friendly).
# Called from update_knowledge.bat: use -EmitCmd so SET lines apply in the parent CMD session.
# See scripts/rag_pipeline/ACTIVATION.md and windows/INSTITUTIONAL.md.
param(
    [switch]$EmitCmd
)

function Get-RagPerfValues {
    $profile = if ($env:HERMES_RAG_PERF_PROFILE) { $env:HERMES_RAG_PERF_PROFILE.Trim().ToLowerInvariant() } else { 'balanced' }

    $cpu = [Environment]::ProcessorCount
    if ($cpu -lt 1) { $cpu = 4 }

    $workers = $null
    $embedBatch = $null
    $heartbeat = $null

    switch ($profile) {
        'safe' {
            $workers = 1
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
            Write-Host "[WARN] Unknown HERMES_RAG_PERF_PROFILE='$profile'; using balanced"
            $profile = 'balanced'
            $half = [Math]::Floor($cpu / 2)
            $workers = [Math]::Min([Math]::Max($half, 2), 8)
            $embedBatch = 64
            $heartbeat = 3
        }
    }

    if ($profile -ne 'off') {
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
        Profile    = $profile
        Cpu        = $cpu
        Workers    = $env:HERMES_RAG_CONVERT_WORKERS
        EmbedBatch = $env:HERMES_RAG_EMBED_BATCH
        Heartbeat  = $env:HERMES_RAG_CONVERT_HEARTBEAT_SEC
    }
}

$vals = Get-RagPerfValues

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
} else {
    Write-Host $info
}

exit 0
