# Toont welke Hermes-checkout actief is (dev vs install-clone) en MCP-config locatie.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "rag_python_resolve.ps1")

$devRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$installClone = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent"
$nousClone = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent"

Write-Host "=== Hermes RAG diagnose ===" -ForegroundColor Cyan
Write-Host "Dev-repo (fork):     $devRoot"
if (Test-Path $installClone) {
    Push-Location $installClone
    $o = (git remote get-url origin 2>$null)
    $c = (git log -1 --oneline 2>$null)
    Pop-Location
    Write-Host "LOCALAPPDATA clone:  $installClone"
    Write-Host "  origin: $o"
    Write-Host "  HEAD:   $c"
} else {
    Write-Host "LOCALAPPDATA clone:  (ontbreekt)"
}

$py = Get-HermesCondaPython
Write-Host "Conda python:        $(if ($py) { $py } else { '(niet gevonden)' })"

# Hermes gebruikt op Windows vaak %LOCALAPPDATA%\hermes (niet altijd ~/.hermes).
$cfgPaths = @(
    (Join-Path $env:LOCALAPPDATA "hermes\config.yaml"),
    (Join-Path $env:USERPROFILE ".hermes\config.yaml")
)
foreach ($cfg in $cfgPaths) {
    if (Test-Path -LiteralPath $cfg) {
        Write-Host "Config:              $cfg" -ForegroundColor Green
        $hit = Select-String -Path $cfg -Pattern "lancedb-knowledge" -Quiet
        Write-Host "  lancedb-knowledge: $(if ($hit) { 'JA' } else { 'NEE' })"
    }
}

Write-Host ""
Write-Host "Aanbevolen: start Hermes via windows\launch_hermes.bat in DEV-repo." -ForegroundColor Yellow
Write-Host "MCP fix: install_rag_extras.ps1 -RepoRoot `"$devRoot`""
