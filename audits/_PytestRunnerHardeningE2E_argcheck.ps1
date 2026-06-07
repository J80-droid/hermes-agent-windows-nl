$ErrorActionPreference = 'Stop'
$repo = $args[0]
Set-Location -LiteralPath $repo
. (Join-Path $repo 'windows\HermesShellCommon.ps1')
. (Join-Path $repo 'windows\HermesPythonPolicy.ps1')
. (Join-Path $repo 'windows\scripts\Invoke-HermesPytestFromManifest.ps1')
$cfg = Get-HermesPytestForkGateConfig -RepoRoot $repo -Mode upstream
$junit = Join-Path $repo 'windows/tests/pytest_upstream_junit.xml'
$extra = @('--maxfail=50', ('--junitxml=' + $junit))
$argSplat = @{ Config = $cfg; ExtraArgs = $extra }
$pytestArgList = Get-HermesPytestArgsFromConfig @argSplat
$tail = @($pytestArgList | Select-Object -Last 2)
if ($tail.Count -ne 2) { exit 2 }
if ($tail[0] -notmatch '^--maxfail=[0-9]+$') { exit 3 }
if ($tail[1] -notmatch '^--junitxml=') { exit 4 }
exit 0
