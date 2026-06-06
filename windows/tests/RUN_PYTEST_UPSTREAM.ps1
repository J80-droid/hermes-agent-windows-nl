# Hermes Agent — upstream pytest parity (volledige tests/). Diagnostiek met -ReportOnly (exit 0 altijd).
param(
    [switch]$ReportOnly,
    [int]$MaxFail = 0
)

$ErrorActionPreference = 'Stop'

$testsDir = $PSScriptRoot
$windowsDir = Split-Path -Parent $testsDir
$repoRoot = (Resolve-Path (Join-Path $windowsDir '..')).Path
Set-Location -LiteralPath $repoRoot

. (Join-Path $windowsDir 'HermesShellCommon.ps1')
. (Join-Path $windowsDir 'HermesPythonPolicy.ps1')
. (Join-Path $windowsDir 'scripts/Invoke-HermesPytestFromManifest.ps1')

$logPath = Join-Path $PSScriptRoot 'RUN_PYTEST_upstream.log'
Write-Host "Log: $logPath" -ForegroundColor DarkGray
if ($ReportOnly) {
    Write-Host 'ReportOnly: exit 0 ook bij failures (Linux CI = upstream waarheid).' -ForegroundColor DarkGray
}

$upstreamArgs = @{}
if ($ReportOnly) { $upstreamArgs['ReportOnly'] = $true }
if ($MaxFail -gt 0) { $upstreamArgs['MaxFail'] = $MaxFail }

Invoke-HermesPytestUpstream -RepoRoot $repoRoot @upstreamArgs @args 2>&1 | Tee-Object -FilePath $logPath
exit $LASTEXITCODE
