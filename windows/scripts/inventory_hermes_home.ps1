<#
.SYNOPSIS
    Inventarisatie split-home: runtime vs legacy, config drift, env keys, gateway, auth.
.NOTES
    Schrijft JSON naar %LOCALAPPDATA%\hermes\logs\home_inventory_<timestamp>.json
#>
param(
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
. (Join-Path $scriptDir 'HermesHomeCommon.ps1')

$runtimeRoot = Get-HermesRuntimeRoot
$legacyRoot = Get-HermesLegacyRoot
$runtimeCfg = Get-HermesCanonicalConfigPath
$legacyCfg = Get-HermesLegacyConfigPath

function Test-EnvKeyActive {
    param([string]$EnvPath, [string]$KeyName)
    if (-not (Test-Path -LiteralPath $EnvPath)) { return $false }
    foreach ($line in (Get-Content -LiteralPath $EnvPath -Encoding UTF8)) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith('#')) { continue }
        if ($t -match "^\s*$KeyName\s*=") {
            $val = ($t -split '=', 2)[1].Trim().Trim('"').Trim("'")
            return [bool]$val -and $val -notmatch 'your_.*_here'
        }
    }
    return $false
}

$userHome = [Environment]::GetEnvironmentVariable('HERMES_HOME', 'User')
$procHome = $env:HERMES_HOME
$auth = Test-HermesAuthJsonHealth -Root $runtimeRoot
$driftOk = Test-HermesConfigDrift -Quiet
$gatewayOk = Test-HermesGatewayHomeAlignment -Quiet

$report = [ordered]@{
    timestamp_utc     = (Get-Date).ToUniversalTime().ToString('o')
    runtime_root      = $runtimeRoot
    legacy_root       = $legacyRoot
    user_hermes_home  = $userHome
    process_hermes_home = $procHome
    runtime_config    = $runtimeCfg
    runtime_config_exists = (Test-Path -LiteralPath $runtimeCfg)
    legacy_config     = $legacyCfg
    legacy_config_exists = (Test-Path -LiteralPath $legacyCfg)
    auxiliary_fingerprint_runtime = Get-HermesConfigAuxiliaryFingerprint -ConfigPath $runtimeCfg
    auxiliary_fingerprint_legacy  = Get-HermesConfigAuxiliaryFingerprint -ConfigPath $legacyCfg
    config_drift_ok   = $driftOk
    auth_ok           = $auth.Ok
    auth_message      = $auth.Message
    gateway_aligned   = $gatewayOk
    env_google_runtime = Test-EnvKeyActive -EnvPath (Join-Path $runtimeRoot '.env') -KeyName 'GOOGLE_API_KEY'
    env_google_legacy  = Test-EnvKeyActive -EnvPath (Join-Path $legacyRoot '.env') -KeyName 'GOOGLE_API_KEY'
    env_openrouter_runtime = Test-EnvKeyActive -EnvPath (Join-Path $runtimeRoot '.env') -KeyName 'OPENROUTER_API_KEY'
    env_openrouter_legacy  = Test-EnvKeyActive -EnvPath (Join-Path $legacyRoot '.env') -KeyName 'OPENROUTER_API_KEY'
    gateway_cmd_paths = @(Get-HermesGatewayCmdPaths)
}

$logDir = Join-Path $runtimeRoot 'logs'
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$outPath = Join-Path $logDir ('home_inventory_' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $outPath -Encoding UTF8

if (-not $Quiet) {
    Write-Host '=== Hermes home inventory ===' -ForegroundColor Cyan
    Write-Host ('Runtime: ' + $runtimeRoot)
    Write-Host ('Legacy:  ' + $legacyRoot)
    Write-Host ('User HERMES_HOME: ' + $(if ($userHome) { $userHome } else { '(niet gezet)' }))
    Write-Host ('Config drift OK: ' + $driftOk)
    if (-not $auth.Ok) {
        Write-Host ('[WARN] ' + $auth.Message) -ForegroundColor Yellow
        Write-Host '       Fix: windows\FIX_GEMINI_CREDENTIAL_POOL.bat' -ForegroundColor Yellow
    } else {
        Write-Host ('Auth OK: ' + $auth.Message)
    }
    Write-Host ('Gateway aligned: ' + $gatewayOk)
    Write-Host ('Report: ' + $outPath) -ForegroundColor Green
}

if (-not $driftOk) { exit 1 }
if (-not $auth.Ok) { exit 2 }
exit 0
