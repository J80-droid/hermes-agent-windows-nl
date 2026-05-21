# Filter bekende PyTorch/transformers-ruis uit RAG-ingest console + log.
function Test-RagIngestNoiseLine {
    param([string]$Line)
    if (-not $Line) { return $false }
    if ($env:HERMES_RAG_QUIET_TORCH -eq '0') { return $false }
    return $Line -match 'KernelPreference|register_constant\(\) on Enum|torch\\utils\\_pytree'
}
