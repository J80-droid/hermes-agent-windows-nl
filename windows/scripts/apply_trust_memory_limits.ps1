# Idempotent: raise memory char limits for Trust & Forensic protocol.
param(
    [string]$HermesRoot = ''
)

$ErrorActionPreference = 'Stop'

function Get-HermesRoot {
    param([string]$OverrideRoot = '')
    if ($OverrideRoot.Trim()) { return (Resolve-Path -LiteralPath $OverrideRoot.Trim()).Path }
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

$root = Get-HermesRoot -OverrideRoot $HermesRoot
$configPath = Join-Path $root 'config.yaml'
if (-not (Test-Path -LiteralPath $configPath)) {
    Write-Error "config.yaml ontbreekt: $configPath"
}

$content = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8
$changed = $false

if ($content -match '(?m)^(\s*)memory_char_limit:\s*\d+') {
    $new = $content -replace '(?m)^(\s*)memory_char_limit:\s*\d+', '${1}memory_char_limit: 4000'
    if ($new -ne $content) { $content = $new; $changed = $true }
} elseif ($content -match '(?m)^memory:\s*$') {
    $content = $content -replace '(?m)^(memory:\s*\r?\n)', "`$1  memory_char_limit: 4000`r`n"
    $changed = $true
}

if ($content -match '(?m)^(\s*)user_char_limit:\s*\d+') {
    $new = $content -replace '(?m)^(\s*)user_char_limit:\s*\d+', '${1}user_char_limit: 1800'
    if ($new -ne $content) { $content = $new; $changed = $true }
}

if ($changed) {
    Set-Content -LiteralPath $configPath -Value $content -Encoding UTF8 -NoNewline
    Write-Host '[OK]memory limits: memory_char_limit=4000 user_char_limit=1800' -ForegroundColor Green
} else {
    Write-Host '[OK] memory limits al op doelwaarde' -ForegroundColor Green
}
