#requires -Version 5.1
# Niet-interactieve renderer verify (diagnose + score) na POST_GIT_PULL.
param(
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$winDir = Split-Path -Parent $scriptDir

. (Join-Path $winDir 'HermesShellCommon.ps1')
. (Join-Path $winDir 'HermesPythonPolicy.ps1')

try {
    if (-not $RepoRoot) {
        $RepoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
    } else {
        $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
    }
} catch {
    Write-HermesFail ('Ongeldig RepoRoot: ' + $_.Exception.Message)
    exit 1
}

$py = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
if (-not $py) {
    Write-HermesErr 'Geen Hermes Python  - REPAIR_PYTHON.bat'
    exit 1
}

$diag = Join-Path $RepoRoot 'scripts\diagnose_renderer.py'
$score = Join-Path $RepoRoot 'scripts\score_institutional_render.py'
if (-not (Test-Path -LiteralPath $diag)) {
    Write-HermesFail ('Ontbreekt: ' + $diag)
    exit 1
}
if (-not (Test-Path -LiteralPath $score)) {
    Write-HermesFail ('Ontbreekt: ' + $score)
    exit 1
}

Write-HermesInfo 'Institutional verify: diagnose_renderer --verify ...'
& $py $diag --verify
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-HermesInfo 'Institutional verify: score_institutional_render --verify ...'
& $py $score --verify
exit $LASTEXITCODE
