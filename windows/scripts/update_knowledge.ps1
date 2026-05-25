# RAG-ingest via domains.yaml (%USERPROFILE%\data\domains.yaml)
param(
    [string[]]$Domain = @(),
    [switch]$All,
    [switch]$List,
    [switch]$McpVerifyOnly,
    [switch]$SkipMcpVerify,
    [switch]$MediaOnly
)

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'rag\rag_institutional_env.ps1')
. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$env:HERMES_REPO = $repo

$domainsYaml = if ($env:HERMES_DOMAINS_YAML) { $env:HERMES_DOMAINS_YAML } else { Join-Path $env:USERPROFILE 'data\domains.yaml' }
$py = Resolve-HermesPythonExe -RepoRoot $repo -RequirePip
$runner = Join-Path $repo 'scripts\rag_pipeline\run_domains_ingest.py'

if (-not (Test-Path -LiteralPath $py)) {
    Write-Host ('[ERROR] ' + 'Python niet gevonden: ' + $py) -ForegroundColor Red
    exit 1
}
if (-not (Test-Path -LiteralPath $runner)) {
    Write-Host ('[ERROR] ' + 'Runner niet gevonden: ' + $runner) -ForegroundColor Red
    exit 1
}
if (-not (Test-Path -LiteralPath $domainsYaml)) {
    Write-Host ('[ERROR] ' + 'domains.yaml niet gevonden: ' + $domainsYaml) -ForegroundColor Red
    Write-Host "        Maak %USERPROFILE%\data\domains.yaml aan (zie repo docs)." -ForegroundColor Yellow
    exit 1
}

$env:HERMES_DOMAINS_YAML = $domainsYaml

# Institutioneel: profiel-mcp_servers altijd in sync met domains.yaml vóór ingest/MCP-test
$syncCli = Join-Path $repo 'scripts\rag_pipeline\sync_profile_mcp_from_domains.py'
if ((Test-Path -LiteralPath $syncCli) -and (-not $List)) {
    Write-Host '[INFO] Sync profiel mcp_servers vanuit domains.yaml...' -ForegroundColor Cyan
    & $py $syncCli --domains-yaml $domainsYaml
    if (Test-NativeCommandFailed) { exit $LASTEXITCODE }
}

$argList = @($runner, '--domains-yaml', $domainsYaml)
if ($SkipMcpVerify) { $env:HERMES_RAG_SKIP_MCP_VERIFY = '1' }
if ($List) { $argList += '--list' }
elseif ($McpVerifyOnly) {
    if ($All) { $argList += '--all' }
    elseif ($Domain.Count -gt 0) {
        foreach ($d in $Domain) { $argList += '--domain', $d }
    } else { $argList += '--all' }
    $argList += '--mcp-verify-only'
}
elseif ($All) { $argList += '--all' }
elseif ($Domain.Count -gt 0) {
    foreach ($d in $Domain) { $argList += '--domain', $d }
    if ($MediaOnly) { $argList += '--media-only' }
} else {
    Write-Host '[ERROR] Geef -All, -Domain naam, -List, of -McpVerifyOnly' -ForegroundColor Red
    exit 1
}

& $py @argList
exit $LASTEXITCODE
