#requires -Version 5.1
# Unit tests: Invoke-HermesPytestFromManifest.ps1 (geïsoleerd, geen live pytest).
# Draai: powershell -NoProfile -ExecutionPolicy Bypass -File windows/tests/HermesPytestFromManifest.Unit.Tests.ps1
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$commonPath = Join-Path $repoRoot 'windows/HermesShellCommon.ps1'
$manifestPath = Join-Path $repoRoot 'windows/scripts/Invoke-HermesPytestFromManifest.ps1'

$script:UnitFailed = 0

. $commonPath
. $manifestPath

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        Write-Host ('FAIL: ' + $Message) -ForegroundColor Red
        $script:UnitFailed++
    }
}

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) {
        Write-Host ('FAIL: ' + $Message + " (expected='$Expected' actual='$Actual')") -ForegroundColor Red
        $script:UnitFailed++
    }
}

function Get-TestPytestConfigObject {
    param(
        [string[]]$Paths = @('tests/sample.py'),
        [string[]]$Ignores = @(),
        [string]$Markers = 'not e2e'
    )
    return [pscustomobject]@{
        mode    = 'gate'
        paths   = $Paths
        ignores = $Ignores
        markers = $Markers
    }
}

# --- Get-HermesPytestArgsFromConfig happy path ---
$cfg = Get-TestPytestConfigObject -Paths @('tests/a.py', 'tests/b.py') -Ignores @('tests/e2e')
$args = Get-HermesPytestArgsFromConfig -Config $cfg
Assert-True ($args[0] -eq 'tests/a.py') 'first path'
Assert-True ($args -contains '--ignore=tests/e2e') 'ignore flag'
Assert-True ($args -contains '-m') 'markers flag present'
Assert-True ($args -contains 'not e2e') 'markers value'
Assert-True ($args -contains '-n') 'xdist disabled -n'
Assert-True ($args -contains '0') 'xdist 0'

# --- upstream extra args stay separate (regression PS 5.1 @() merge) ---
$upstreamExtra = @(
    '--maxfail=50'
    '--junitxml=C:\tmp\junit.xml'
)
Assert-Equal 2 $upstreamExtra.Count 'upstreamExtra count'
$argSplat = @{ Config = $cfg; ExtraArgs = $upstreamExtra }
$merged = Get-HermesPytestArgsFromConfig @argSplat
$tail = @($merged | Select-Object -Last 2)
Assert-Equal '--maxfail=50' $tail[0] 'maxfail arg separate'
Assert-Equal '--junitxml=C:\tmp\junit.xml' $tail[1] 'junitxml arg separate'

# --- empty / null ExtraArgs ignored ---
$argSplatEmpty = @{ Config = $cfg; ExtraArgs = @() }
$noExtra = Get-HermesPytestArgsFromConfig @argSplatEmpty
$argSplatNull = @{ Config = $cfg; ExtraArgs = @('', $null, '  ') }
$withNull = Get-HermesPytestArgsFromConfig @argSplatNull
Assert-Equal $noExtra.Count $withNull.Count 'blank ExtraArgs stripped'

# --- no markers when empty ---
$cfgNoMark = Get-TestPytestConfigObject -Markers ''
$argsNoMark = Get-HermesPytestArgsFromConfig -Config $cfgNoMark
Assert-True (-not ($argsNoMark -contains '-m')) 'no -m when markers empty'

# --- Get-HermesPytestForkGateConfig throws on missing loader ---
$badRoot = Join-Path $env:TEMP ('hermes_pytest_unit_' + [Guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $badRoot -Force | Out-Null
$threw = $false
try {
    Get-HermesPytestForkGateConfig -RepoRoot $badRoot -Mode gate
} catch {
    $threw = $_.Exception.Message -match 'manifest loader ontbreekt'
}
Assert-True $threw 'missing loader throws'
Remove-Item -LiteralPath $badRoot -Recurse -Force -ErrorAction SilentlyContinue

if ($script:UnitFailed -gt 0) {
    Write-Host "UNIT FAILURES: $($script:UnitFailed)" -ForegroundColor Red
    exit 1
}
Write-Host 'HermesPytestFromManifest unit tests: ALL PASS' -ForegroundColor Green
exit 0
