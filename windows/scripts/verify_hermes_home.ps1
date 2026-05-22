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

if ($failed) { exit 1 }
exit 0
