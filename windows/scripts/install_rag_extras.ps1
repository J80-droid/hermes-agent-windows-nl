# Installeert pyproject extra [rag] en registreert lancedb-knowledge MCP (idempotent).
param(
    [string]$RepoRoot = "",
    [switch]$SkipPip,
    [switch]$SkipMcp,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

function Write-RagMsg([string]$Text, [string]$Color = "Gray") {
    if ($Quiet) { return }
    Write-Host $Text -ForegroundColor $Color
}

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "pyproject.toml"))) {
    Write-Error "Geen pyproject.toml in RepoRoot: $RepoRoot"
}

$Python = $env:HERMES_PYTHON
if (-not $Python) {
    $candidates = @(
        (Join-Path $env:USERPROFILE "miniconda3\envs\hermes-env\python.exe"),
        (Join-Path $env:LOCALAPPDATA "miniconda3\envs\hermes-env\python.exe")
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) { $Python = $c; break }
    }
}

if (-not $SkipPip) {
    if (-not $Python) {
        Write-RagMsg "[WARN] Geen hermes-env python — sla pip install -e `".[rag]`" over." "Yellow"
    } else {
        Write-RagMsg "[INFO] RAG-dependencies installeren (pyproject extra rag)..." "Cyan"
        & $Python -m pip install -e "${RepoRoot}[rag]"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "pip install -e `"${RepoRoot}[rag]`" mislukt (exit $LASTEXITCODE)."
        }
        Write-RagMsg "[OK] RAG-dependencies geïnstalleerd." "Green"
    }
}

if (-not $SkipMcp) {
    if (-not (Get-Command hermes -ErrorAction SilentlyContinue)) {
        Write-RagMsg "[WARN] `hermes` niet op PATH — MCP-registratie overgeslagen. Open nieuw venster na install." "Yellow"
    } else {
        $reg = Join-Path $PSScriptRoot "register_lancedb_mcp.ps1"
        & powershell -ExecutionPolicy Bypass -File $reg -RepoRoot $RepoRoot -Quiet:$Quiet
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

if (-not $Quiet) {
    Write-RagMsg "[OK] RAG-extras klaar (pip + MCP waar mogelijk)." "Green"
}
