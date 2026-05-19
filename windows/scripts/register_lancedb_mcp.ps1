# Registreer lancedb-knowledge MCP (absoluut scriptpad + env; non-interactief via Python).

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

    Write-Error "Geen hermes-env python gevonden. Zet HERMES_PYTHON of installeer conda env hermes-env."

}



$mcpScript = Join-Path $RepoRoot "scripts\rag_pipeline\mcp_server.py"

if (-not (Test-Path -LiteralPath $mcpScript)) {

    Write-Error "MCP-script ontbreekt: $mcpScript"

}



if (-not $env:HERMES_LANCEDB_PATH) {

    $env:HERMES_LANCEDB_PATH = Join-Path $env:USERPROFILE "data\my_lancedb"

}



$regPy = Join-Path $RepoRoot "scripts\rag_pipeline\register_mcp_config.py"

& $Python $regPy --repo-root $RepoRoot --python $Python

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



if (-not $Quiet) {

    Write-Host "[OK] MCP lancedb-knowledge geregistreerd. Start een nieuwe Hermes-sessie."

}


