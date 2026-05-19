# Eenmalig: registreer lancedb-knowledge MCP (hermes-env python, repo-root args).
param(
    [string]$RepoRoot = "",
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}
Set-Location $RepoRoot

$Python = $env:HERMES_PYTHON
if (-not $Python) {
    $candidates = @(
        (Join-Path $env:USERPROFILE "miniconda3\envs\hermes-env\python.exe"),
        (Join-Path $env:LOCALAPPDATA "miniconda3\envs\hermes-env\python.exe")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $Python = $c; break }
    }
}
if (-not $Python) {
    Write-Error "Geen hermes-env python gevonden. Zet HERMES_PYTHON of installeer conda env hermes-env."
}

$existing = & hermes mcp list 2>&1 | Out-String
if ($existing -match "lancedb-knowledge") {
    if (-not $Quiet) { Write-Host "[OK] MCP lancedb-knowledge staat al geregistreerd." }
    exit 0
}

$mcpScript = "scripts/rag_pipeline/mcp_server.py"
& hermes mcp add lancedb-knowledge --command $Python --args $mcpScript
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not $Quiet) {
    Write-Host "[OK] MCP lancedb-knowledge geregistreerd. Start een nieuwe Hermes-sessie."
}
