# Installeert pyproject [rag] op conda hermes-env (institutioneel), MCP-config, modelcache (idempotent).
param(
    [string]$RepoRoot = "",
    [switch]$SkipPip,
    [switch]$SkipMcp,
    [switch]$SkipModelWarm,
    [switch]$Quiet
)

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\HermesPythonPolicy.ps1")

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

[void](Invoke-HermesQuarantineBrokenVenv -RepoRoot $RepoRoot -Quiet:$Quiet)

$pythons = @(Get-HermesRagPython -RepoRoot $RepoRoot)
if ($pythons.Count -eq 0) {
    Write-RagMsg '[WARN] Geen conda hermes-env - REPAIR_PYTHON.bat of: conda activate hermes-env' 'Yellow'
}

if (-not $SkipPip) {
    $installed = 0
    foreach ($py in $pythons) {
        if (-not (Test-HermesPythonHasPip -PythonExe $py)) {
            Write-RagMsg ('[WARN] Geen pip op {0} - overgeslagen.' -f $py) 'Yellow'
            continue
        }
        Write-RagMsg ('[INFO] RAG-deps via: {0}' -f $py) 'Cyan'
        & $py -m pip install -e ($RepoRoot + '[rag]')
        if (Test-NativeCommandFailed) {
            Write-Error ('pip install -e [rag] mislukt voor {0} (exit {1}).' -f $py, $LASTEXITCODE)
        }
        & $py -m pip install 'markitdown[all]==0.1.5'
        if (Test-NativeCommandFailed) {
            Write-RagMsg '[WARN] markitdown[all] apart mislukt - Office/PDF kan beperkt zijn.' 'Yellow'
        }
        & $py -m pip install "colorama>=0.4.6" "tqdm>=4.66"
        if (Test-NativeCommandFailed) {
            Write-RagMsg '[WARN] colorama/tqdm mislukt - RAG-terminal kan zonder kleuren/balk.' 'Yellow'
        }
        $installed++
    }
    if ($installed -gt 0) {
        Write-RagMsg ('[OK] RAG-dependencies op {0} interpreter(s).' -f $installed) 'Green'
    } elseif ($pythons.Count -eq 0) {
        Write-RagMsg '[WARN] Geen Python met pip — conda: conda activate hermes-env; pip install -e .[rag]' 'Yellow'
    }
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        Write-RagMsg '[WARN] ffmpeg niet op PATH - Whisper/media kan falen.' 'Yellow'
    }
}

if (-not $SkipModelWarm) {
    $py = ($pythons | Where-Object { Test-HermesPythonHasPip -PythonExe $_ } | Select-Object -First 1)
    if ($py) {
        Write-RagMsg '[INFO] Embedding-modelcache warmen...' 'Cyan'
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'SilentlyContinue'
        try {
            $null = & $py -c 'from sentence_transformers import SentenceTransformer; SentenceTransformer("all-MiniLM-L6-v2")' 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-RagMsg '[OK] Modelcache klaar.' 'Green'
            } else {
                Write-RagMsg ('[WARN] Modelcache warmen mislukt (exit {0}).' -f $LASTEXITCODE) 'Yellow'
            }
        } finally {
            $ErrorActionPreference = $prevEap
        }
    }
}

if (-not $SkipMcp) {
    $reg = Join-Path $PSScriptRoot "register_lancedb_mcp.ps1"
    if ($Quiet) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $reg -RepoRoot $RepoRoot -Quiet
    } else {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $reg -RepoRoot $RepoRoot
    }
    if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
}

if (-not $Quiet) {
    Write-RagMsg '[OK] RAG-extras klaar.' 'Green'
    Write-RagMsg ('  Dev-repo: {0}' -f $RepoRoot) 'DarkGray'
    $cloneRoot = Join-Path $env:LOCALAPPDATA 'hermes\hermes-agent'
    Write-RagMsg ('  Andere clone: {0}' -f $cloneRoot) 'DarkGray'
}
