<#
.SYNOPSIS
    Controleert HERMES_HOME (root, geen profiles\*) active_profile BOM auth config drift gateway.
.EXIT
    0 = OK, 1 = probleem
#>
param(
    [switch]$SkipDrift,
    [switch]$StrictDrift,
    [switch]$AutoRepairModelProvider
)

$ErrorActionPreference = 'Stop'
$failed = $false
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
. (Join-Path $scriptDir 'HermesHomeCommon.ps1')

$root = Get-HermesRuntimeRoot
Write-Host ('[INFO] Runtime root: ' + $root) -ForegroundColor Cyan

$userHome = [Environment]::GetEnvironmentVariable('HERMES_HOME', 'User')
if ($userHome -and (Test-HermesProfileSubdirPath $userHome)) {
    Write-Host ('[FAIL] User HERMES_HOME wijst naar profielmap: ' + $userHome + ' (verwacht root: ' + $root + ')') -ForegroundColor Red
    Write-Host '       Fix: SWITCH_PROFILE.bat <naam> of hermes profile use <naam> --fix-hermes-home' -ForegroundColor Yellow
    $failed = $true
} elseif ($userHome) {
    $normUser = $userHome.TrimEnd('\')
    $normRoot = $root.TrimEnd('\')
    if ($normUser -ne $normRoot) {
        Write-Host ('[WARN] User HERMES_HOME (' + $userHome + ') wijkt af van runtime root (' + $root + ')') -ForegroundColor Yellow
    } else {
        Write-Host ('[OK] User HERMES_HOME: ' + $userHome) -ForegroundColor Green
    }
} else {
    Write-Host '[OK] User HERMES_HOME niet gezet (launch zet proces-env)' -ForegroundColor Green
}

if ($env:HERMES_HOME -and (Test-HermesProfileSubdirPath $env:HERMES_HOME)) {
    Write-Host ('[FAIL] Proces HERMES_HOME wijst naar profielmap: ' + $($env:HERMES_HOME)) -ForegroundColor Red
    $failed = $true
}

$activePath = Join-Path $root 'active_profile'
if (Test-Path -LiteralPath $activePath) {
    $bytes = [System.IO.File]::ReadAllBytes($activePath)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Write-Host '[FAIL] active_profile heeft UTF-8 BOM' -ForegroundColor Red
        $failed = $true
    } else {
        $name = (Get-Content -LiteralPath $activePath -Raw -Encoding UTF8).Trim()
        Write-Host ('[OK] active_profile: ' + $name) -ForegroundColor Green
    }
} else {
    Write-Host '[OK] active_profile: (default)' -ForegroundColor Green
}

$auth = Test-HermesAuthJsonHealth -Root $root
if (-not $auth.Ok) {
    Write-Host ('[WARN] ' + $auth.Message) -ForegroundColor Yellow
    Write-Host '       Zie: windows\FIX_GEMINI_CREDENTIAL_POOL.bat' -ForegroundColor Yellow
    $authPath = Join-Path $root 'auth.json'
    if (Test-Path -LiteralPath $authPath) {
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $corrupt = "$authPath.corrupt-$stamp"
        try {
            Copy-Item -LiteralPath $authPath -Destination $corrupt -Force
        } catch {
            Write-Verbose $_.Exception.Message
        }
        @'
{
  "version": 1,
  "providers": {}
}
'@ | Set-Content -LiteralPath $authPath -Encoding UTF8 -NoNewline
        Write-Host ('[WARN] auth.json hersteld (backup: ' + $corrupt + ')') -ForegroundColor Yellow
    }
} else {
    Write-Host ('[OK] ' + $auth.Message) -ForegroundColor Green
}

if (-not $SkipDrift) {
    $driftOk = Test-HermesConfigDrift -Strict:$StrictDrift -AutoRepairModelProvider:$AutoRepairModelProvider
    if (-not $driftOk) { $failed = $true }
}

if (-not (Test-HermesGatewayHomeAlignment)) {
    Write-Host '[WARN] Gateway HERMES_HOME niet aligned (niet fatal)' -ForegroundColor Yellow
}

if ($failed) { exit 1 }
exit 0
