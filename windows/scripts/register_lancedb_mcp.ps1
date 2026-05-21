# Verifieer per-domein LanceDB MCP in Hermes-profiles (domains.yaml). Geen monoliet meer.
param(
    [string]$RepoRoot = "",
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "rag_python_resolve.ps1")

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$Python = Get-HermesCondaPython
if (-not $Python) {
    Write-Error "Geen hermes-env python gevonden."
}

$domainsYaml = Join-Path $env:USERPROFILE "data\domains.yaml"
if (-not (Test-Path -LiteralPath $domainsYaml)) {
    Write-Error "domains.yaml ontbreekt: $domainsYaml"
}

$regPy = Join-Path $RepoRoot "scripts\rag_pipeline\register_mcp_config.py"
& $Python $regPy --domains-yaml $domainsYaml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $Quiet) {
    Write-Host "[OK] Per-domein MCP gecontroleerd. Test: windows\scripts\update_knowledge.bat --mcp-test"
}
