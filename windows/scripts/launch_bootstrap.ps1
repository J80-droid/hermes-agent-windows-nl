# Lichtgewicht bootstrap bij Hermes-start (launch_hermes.bat) — geen volledige SETUP.
param(
    [string]$RepoRoot = '',
    [switch]$ForceRagCheck
)

$ErrorActionPreference = 'Stop'
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$stampDir = Join-Path $env:USERPROFILE '.hermes'
$stampFile = Join-Path $stampDir 'launch_bootstrap.stamp'
$pyproject = Join-Path $RepoRoot 'pyproject.toml'
$needRag = $ForceRagCheck.IsPresent

if (-not $needRag -and (Test-Path -LiteralPath $stampFile) -and (Test-Path -LiteralPath $pyproject)) {
    $stampTime = (Get-Item -LiteralPath $stampFile).LastWriteTimeUtc
    $projTime = (Get-Item -LiteralPath $pyproject).LastWriteTimeUtc
    if ($projTime -le $stampTime) { $needRag = $false } else { $needRag = $true }
} elseif (-not (Test-Path -LiteralPath $stampFile)) {
    $needRag = $true
}

$ensurePy = Join-Path $RepoRoot 'windows/scripts/ensure_hermes_python.ps1'
if (Test-Path -LiteralPath $ensurePy) {
    & $ensurePy -RepoRoot $RepoRoot -Quiet
}

if ($needRag) {
    $ragExtras = Join-Path $RepoRoot 'windows/scripts/install_rag_extras.ps1'
    if (Test-Path -LiteralPath $ragExtras) {
        Write-Host '[INFO] RAG/MCP eenmalige sync (pyproject gewijzigd of eerste start)...' -ForegroundColor Cyan
        & $ragExtras -RepoRoot $RepoRoot -Quiet
    }
    if (-not (Test-Path -LiteralPath $stampDir)) {
        New-Item -ItemType Directory -Path $stampDir -Force | Out-Null
    }
    Set-Content -LiteralPath $stampFile -Value (Get-Date -Format 'o') -Encoding utf8
}

exit 0
