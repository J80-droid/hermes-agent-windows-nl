# Installeert pyproject [rag] op alle bekende Python-installaties + MCP + modelcache (idempotent).

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



$pythons = Get-AllHermesRagPythons -RepoRoot $RepoRoot

if ($pythons.Count -eq 0) {

    Write-RagMsg "[WARN] Geen conda hermes-env of .venv gevonden — zet HERMES_PYTHON." "Yellow"

}



if (-not $SkipPip) {

    foreach ($py in $pythons) {

        Write-RagMsg "[INFO] RAG-deps installeren via: $py" "Cyan"

        & $py -m pip install -e "${RepoRoot}[rag]"

        if ($LASTEXITCODE -ne 0) {

            Write-Error "pip install -e `"${RepoRoot}[rag]`" mislukt voor $py (exit $LASTEXITCODE)."

        }

    }

    if ($pythons.Count -gt 0) {

        Write-RagMsg "[OK] RAG-dependencies geïnstalleerd op $($pythons.Count) interpreter(s)." "Green"

    }

    $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue

    if (-not $ffmpeg) {

        Write-RagMsg "[WARN] ffmpeg niet op PATH — media-ingest (Whisper) faalt zonder ffmpeg. Installeer via winget/choco." "Yellow"

    }

}



if (-not $SkipModelWarm) {

    $py = $pythons | Select-Object -First 1

    if ($py) {

        Write-RagMsg "[INFO] Sentence-transformers modelcache warmen (all-MiniLM-L6-v2)..." "Cyan"

        & $py -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" 2>&1 | Out-Null

        if ($LASTEXITCODE -eq 0) {

            Write-RagMsg "[OK] Embedding-modelcache klaar." "Green"

        } else {

            Write-RagMsg "[WARN] Modelcache warmen mislukt — eerste MCP/ingest kan langer duren." "Yellow"

        }

    }

}



if (-not $SkipMcp) {

    if (-not (Get-Command hermes -ErrorAction SilentlyContinue)) {

        Write-RagMsg "[WARN] `hermes` niet op PATH — MCP-registratie overgeslagen. Open nieuw venster na install." "Yellow"

    } else {

        $reg = Join-Path $PSScriptRoot "register_lancedb_mcp.ps1"

        & powershell -NoProfile -ExecutionPolicy Bypass -File $reg -RepoRoot $RepoRoot -Quiet:$Quiet

        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    }

}



if (-not $Quiet) {

    Write-RagMsg "[OK] RAG-extras klaar (pip op conda+uv, MCP, modelcache waar mogelijk)." "Green"

    Write-RagMsg "     Dev-repo: $RepoRoot" "DarkGray"

    Write-RagMsg "     Install-clone: $(Join-Path $env:LOCALAPPDATA 'hermes\hermes-agent')" "DarkGray"

}


