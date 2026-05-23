# Toont actieve Hermes-checkout en per-domein RAG/MCP-status (domains.yaml).
#Requires -Version 5.1
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "rag_python_resolve.ps1")

$devRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$domainsYaml = Join-Path $env:USERPROFILE "data\domains.yaml"

Write-Host "=== Hermes RAG diagnose ===" -ForegroundColor Cyan
Write-Host "Dev-repo:            $devRoot"
Write-Host "domains.yaml:        $domainsYaml"

$py = Get-HermesCondaPython
Write-Host "Conda python:        $(if ($py) { $py } else { '(niet gevonden)' })"

if (Test-Path -LiteralPath $domainsYaml) {
    $runner = Join-Path $devRoot "scripts\rag_pipeline\run_domains_ingest.py"
    if ($py -and (Test-Path -LiteralPath $runner)) {
        Write-Host ""
        Write-Host "Domeinen:" -ForegroundColor Green
        & $py --list --domains-yaml $domainsYaml
    }
} else {
    Write-Host '[WARN]domains.yaml ontbreekt' -ForegroundColor Yellow
}

$profilesRoot = Join-Path $env:LOCALAPPDATA "hermes\profiles"
if (Test-Path -LiteralPath $profilesRoot) {
    Write-Host ""
    Write-Host "Profiles (MCP in config.yaml):" -ForegroundColor Green
    Get-ChildItem -LiteralPath $profilesRoot -Directory | ForEach-Object {
        $cfg = Join-Path $_.FullName "config.yaml"
        if (Test-Path -LiteralPath $cfg) {
            $hits = Select-String -Path $cfg -Pattern "lancedb-" -AllMatches
            $names = ($hits | ForEach-Object { $_.Matches.Value } | Select-Object -Unique) -join ", "
            Write-Host "  $($_.Name): $(if ($names) { $names } else { '(geen lancedb MCP)' })"
        }
    }
}

Write-Host ""
Write-Host "RAG starten: windows/scripts/update_knowledge.bat  (of taakbalk .lnk)" -ForegroundColor Yellow
Write-Host "MCP test:    update_knowledge.bat --mcp-test" -ForegroundColor Yellow
