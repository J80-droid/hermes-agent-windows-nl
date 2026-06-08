# Fork tests/hermes_cli/ hygiene — SSOT: docs/FORK_MERGE_POLICY.md
param(
    [string]$RepoRoot = '',
    [string]$UpstreamRef = 'upstream/main',
    [switch]$PreMerge,
    [switch]$Staged,
    [switch]$Strict,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot '..\HermesNativeInvoke.ps1')
. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')

if (-not $RepoRoot) {
    . (Join-Path $PSScriptRoot 'HermesNousDrift.ps1')
    $RepoRoot = Get-HermesRepoRootFromNousScripts
}

$py = Join-Path $PSScriptRoot 'check_fork_hermes_cli_tests.py'
if (-not (Test-Path -LiteralPath $py)) {
    Write-HermesErr "Ontbreekt: $py"
    exit 1
}

$pythonExe = Resolve-HermesPythonExe -RepoRoot $RepoRoot
if (-not $pythonExe) {
    if ($env:HERMES_AUDIT_PYTHON -and (Test-Path -LiteralPath $env:HERMES_AUDIT_PYTHON)) {
        $pythonExe = $env:HERMES_AUDIT_PYTHON
    } else {
        $pythonExe = 'python'
    }
}

$doPre = $PreMerge -or (-not $PreMerge -and -not $Staged)
$doStaged = $Staged

$pyArgs = @($py, '--repo', $RepoRoot)
if ($doPre) { $pyArgs += '--pre-merge', '--upstream', $UpstreamRef }
if ($doStaged) { $pyArgs += '--staged' }
if ($Strict) { $pyArgs += '--strict' }
if ($Json) { $pyArgs += '--json' }

# Python schrijft pre-merge WARN naar stderr; onder EAP Stop wordt 2>&1 een NativeCommandError.
$code = Invoke-HermesNativeCommand -FilePath $pythonExe -ArgumentList $pyArgs
exit $code
