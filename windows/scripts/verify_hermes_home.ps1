<#
.SYNOPSIS
    Controleert HERMES_HOME (root, geen profiles\*) en active_profile (geen BOM).
.EXIT
    0 = OK, 1 = probleem
#>
$ErrorActionPreference = 'Stop'
$failed = $false

function Test-ProfileSubdirPath {
    param([string]$Path)
    if (-not $Path) { return $false }
    $p = $Path.TrimEnd('\') -replace '/', '\'
    return $p -match '\\profiles\\[a-z0-9][a-z0-9_-]{0,63}$'
}

function Get-HermesRoot {
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

$root = Get-HermesRoot

$userHome = [Environment]::GetEnvironmentVariable('HERMES_HOME', 'User')
if ($userHome -and (Test-ProfileSubdirPath $userHome)) {
    Write-Host "[FAIL] User HERMES_HOME wijst naar profielmap: $userHome (verwacht root: $root)" -ForegroundColor Red
    $failed = $true
} elseif ($userHome) {
    Write-Host "[OK] User HERMES_HOME: $userHome" -ForegroundColor Green
} else {
    Write-Host "[OK] User HERMES_HOME niet gezet (OK)" -ForegroundColor Green
}

if ($env:HERMES_HOME -and (Test-ProfileSubdirPath $env:HERMES_HOME)) {
    Write-Host "[FAIL] Proces HERMES_HOME wijst naar profielmap: $($env:HERMES_HOME)" -ForegroundColor Red
    $failed = $true
}

$activePath = Join-Path $root 'active_profile'
if (Test-Path -LiteralPath $activePath) {
    $bytes = [System.IO.File]::ReadAllBytes($activePath)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Write-Host "[FAIL] active_profile heeft UTF-8 BOM" -ForegroundColor Red
        $failed = $true
    } else {
        $name = (Get-Content -LiteralPath $activePath -Raw -Encoding UTF8).Trim()
        Write-Host "[OK] active_profile: $name" -ForegroundColor Green
    }
} else {
    Write-Host "[OK] active_profile: (default)" -ForegroundColor Green
}

$authPath = Join-Path $root 'auth.json'
if (Test-Path -LiteralPath $authPath) {
    $authRaw = Get-Content -LiteralPath $authPath -Raw -Encoding UTF8
    $authOk = $false
    if ($authRaw.Trim()) {
        try {
            $parsed = $authRaw | ConvertFrom-Json
            $authOk = ($null -ne $parsed) -and (
                ($parsed.PSObject.Properties.Name -contains 'providers') -or
                ($parsed.PSObject.Properties.Name -contains 'credential_pool')
            )
        } catch {
            $authOk = $false
        }
    }
    if (-not $authOk) {
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $corrupt = "$authPath.corrupt-$stamp"
        try {
            Copy-Item -LiteralPath $authPath -Destination $corrupt -Force
        } catch { }
        @'
{
  "version": 1,
  "providers": {}
}
'@ | Set-Content -LiteralPath $authPath -Encoding UTF8 -NoNewline
        Write-Host "[WARN] auth.json was ongeldig - hersteld naar lege store (backup: $corrupt)" -ForegroundColor Yellow
    } else {
        Write-Host '[OK] auth.json parsebaar' -ForegroundColor Green
    }
}

if ($failed) { exit 1 }
exit 0
