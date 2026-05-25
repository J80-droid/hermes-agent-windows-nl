# Na REPAIR_PYTHON: controleer RAG [rag]-deps (niet-blokkerend).
param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$py = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
if (-not $py) {
    if (-not $Quiet) {
        Write-Host '[ERROR] Geen conda hermes-env na repair.' -ForegroundColor Red
    }
    exit 1
}

if (Test-HermesRagExtrasInstalled -PythonExe $py) {
    if (-not $Quiet) {
        Write-Host '[OK] RAG-deps ([rag]) geinstalleerd.' -ForegroundColor Green
    }
    exit 0
}

if (-not $Quiet) {
    Write-Host '[WARN] RAG-deps ([rag]) ontbreken — vereist voor update_knowledge / search_knowledge.' -ForegroundColor Yellow
    Write-Host '  Automatisch bij start/setup, of handmatig:' -ForegroundColor DarkYellow
    Write-Host '    powershell -File windows\scripts\install_rag_extras.ps1' -ForegroundColor DarkYellow
    $answer = Read-Host 'Nu install_rag_extras.ps1 draaien? (J/N)'
    if ($answer -match '^[Jj]') {
        $extras = Join-Path $PSScriptRoot 'install_rag_extras.ps1'
        & $extras -RepoRoot $RepoRoot
        exit $LASTEXITCODE
    }
}
exit 0
