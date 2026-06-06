# Hermes Agent — PSScriptAnalyzer op alle windows\*.ps1 (zelfde helper als RUN_AUDITS.ps1).
# Geen pytest: gebruik dit naast RUN_PYTEST.ps1 (snellere iteratie op Python zonder PS-lint elke keer).
$ErrorActionPreference = 'Stop'

$testsDir = $PSScriptRoot
$windowsDir = Split-Path -Parent $testsDir
$repoRoot = (Resolve-Path (Join-Path $windowsDir '..')).Path
Set-Location -LiteralPath $repoRoot

$pssaHelper = Join-Path $windowsDir 'Invoke-HermesPSScriptAnalyzer.ps1'
. $pssaHelper
exit (Invoke-HermesPSScriptAnalyzer -RepoRoot $repoRoot -IfMissing Fail -FailOnWarning)
