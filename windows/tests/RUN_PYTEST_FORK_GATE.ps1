# Hermes Agent — fork pytest gate (manifest SSOT). Hard poort: exit 0 verplicht.
$ErrorActionPreference = 'Stop'

$testsDir = $PSScriptRoot
$windowsDir = Split-Path -Parent $testsDir
$repoRoot = (Resolve-Path (Join-Path $windowsDir '..')).Path
Set-Location -LiteralPath $repoRoot

. (Join-Path $windowsDir 'HermesShellCommon.ps1')
. (Join-Path $windowsDir 'HermesPythonPolicy.ps1')
. (Join-Path $windowsDir 'scripts/Invoke-HermesPytestFromManifest.ps1')

$logPath = Join-Path $PSScriptRoot 'RUN_PYTEST_fork_gate.log'
Write-Host "Log: $logPath" -ForegroundColor DarkGray

Invoke-HermesPytestGate -RepoRoot $repoRoot @args 2>&1 | Tee-Object -FilePath $logPath
$gateExit = $global:LASTEXITCODE
if ($null -eq $gateExit) { $gateExit = 0 }
exit $gateExit
