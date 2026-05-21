# Institutionele RAG-env defaults (PowerShell-pad). Zie rag_institutional_defaults.py.
function Set-RagInstitutionalEnv {
    [CmdletBinding(SupportsShouldProcess)]
    param([switch]$NonInteractive)
    if (-not $PSCmdlet.ShouldProcess('RAG environment', 'Set', 'Institutional RAG defaults')) { return }
    if (-not $env:HERMES_RAG_LIVE_STALE_SEC) { $env:HERMES_RAG_LIVE_STALE_SEC = '120' }
    if (-not $env:HERMES_RAG_QUIET_TORCH) { $env:HERMES_RAG_QUIET_TORCH = '1' }
    if (-not $env:HERMES_RAG_PERF_PROFILE) { $env:HERMES_RAG_PERF_PROFILE = 'safe' }
    if (-not $env:TRANSFORMERS_VERBOSITY) { $env:TRANSFORMERS_VERBOSITY = 'error' }
    if (-not $env:TOKENIZERS_PARALLELISM) { $env:TOKENIZERS_PARALLELISM = 'false' }
    if ($NonInteractive -and -not $env:HERMES_NONINTERACTIVE) { $env:HERMES_NONINTERACTIVE = '1' }
}

Set-RagInstitutionalEnv
