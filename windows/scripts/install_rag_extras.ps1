# Installeert pyproject [rag] op conda + uv .venv, MCP-config, modelcache (idempotent).
param(
    [string]$RepoRoot = "",
    [switch]$SkipPip,
    [switch]$SkipMcp,
    [switch]$SkipModelWarm,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "rag_python_resolve.ps1")

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

$pythons = @(Get-AllHermesRagPythons -RepoRoot $RepoRoot)
if ($pythons.Count -eq 0) {
    Write-RagMsg "[WARN] Geen conda hermes-env of .venv gevonden - zet HERMES_PYTHON." "Yellow"
}

if (-not $SkipPip) {
    foreach ($py in $pythons) {
        & $py -m pip --version 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-RagMsg "[WARN] Geen pip op $py - overgeslagen (gebruik conda of: uv pip install -e `".[rag]`")." "Yellow"
            continue
        }
        Write-RagMsg "[INFO] RAG-deps via: $py" "Cyan"
        & $py -m pip install -e "${RepoRoot}[rag]"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "pip install -e [rag] mislukt voor $py (exit $LASTEXITCODE)."
        }
        & $py -m pip install "markitdown[all]==0.1.5"
        if ($LASTEXITCODE -ne 0) {
            Write-RagMsg "[WARN] markitdown[all] apart mislukt - Office/PDF kan beperkt zijn." "Yellow"
        }
        & $py -m pip install "colorama>=0.4.6" "tqdm>=4.66"
        if ($LASTEXITCODE -ne 0) {
            Write-RagMsg "[WARN] colorama/tqdm mislukt - RAG-terminal kan zonder kleuren/balk." "Yellow"
        }
    }
    if ($pythons.Count -gt 0) {
        $n = $pythons.Count
        Write-RagMsg "[OK] RAG-dependencies op $n interpreter(s)." "Green"
    }
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        Write-RagMsg "[WARN] ffmpeg niet op PATH - Whisper/media kan falen." "Yellow"
    }
}

if (-not $SkipModelWarm) {
    $py = $pythons | Select-Object -First 1
    if ($py) {
        Write-RagMsg "[INFO] Embedding-modelcache warmen..." "Cyan"
        & $py -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-RagMsg "[OK] Modelcache klaar." "Green"
        } else {
            Write-RagMsg "[WARN] Modelcache warmen mislukt." "Yellow"
        }
    }
}

if (-not $SkipMcp) {
    $reg = Join-Path $PSScriptRoot "register_lancedb_mcp.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $reg -RepoRoot $RepoRoot -Quiet:$Quiet
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $Quiet) {
    Write-RagMsg "[OK] RAG-extras klaar." "Green"
    Write-RagMsg "  Dev-repo: $RepoRoot" "DarkGray"
    Write-RagMsg "  Andere clone: $(Join-Path $env:LOCALAPPDATA 'hermes\hermes-agent')" "DarkGray"
}
