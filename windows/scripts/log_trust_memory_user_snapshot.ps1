# Post trust-sync: log eerste USER.md-regel per profiel (en root) voor snelle controle.
param(
    [string]$HermesRoot = '',
    [int]$MaxPreview = 96,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'

function Get-HermesRoot {
    param([string]$OverrideRoot = '')
    if ($OverrideRoot) {
        return (Resolve-Path -LiteralPath $OverrideRoot).Path
    }
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

function Get-FirstUserLine {
    param([string]$UserPath)
    if (-not (Test-Path -LiteralPath $UserPath)) { return $null }
    $raw = Get-Content -LiteralPath $UserPath -Raw -Encoding UTF8
    if (-not $raw.Trim()) { return '' }
    $firstEntry = ($raw -split '(?m)^§\s*$' | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -First 1)
    if (-not $firstEntry) { return '' }
    return ($firstEntry -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -First 1)
}

function Format-Preview {
    param([string]$Text, [int]$Max)
    if (-not $Text) { return '(leeg)' }
    $one = ($Text -replace '\s+', ' ').Trim()
    if ($one.Length -le $Max) { return $one }
    return $one.Substring(0, $Max) + '...'
}

$root = Get-HermesRoot -OverrideRoot $HermesRoot
$failures = 0
$targets = @(
    @{ Name = 'root'; UserPath = Join-Path $root 'memories/USER.md' }
)

$profilesDir = Join-Path $root 'profiles'
if (Test-Path -LiteralPath $profilesDir) {
    Get-ChildItem -LiteralPath $profilesDir -Directory | Sort-Object Name | ForEach-Object {
        $targets += @{ Name = $_.Name; UserPath = Join-Path $_.FullName 'memories/USER.md' }
    }
}

if (-not $Quiet) {
    Write-Host '=== Trust memory USER snapshot (regel 1 per profiel) ===' -ForegroundColor Cyan
}

foreach ($t in $targets) {
    $line = Get-FirstUserLine -UserPath $t.UserPath
    if ($null -eq $line) {
        Write-Host ('[FAIL] ' + $($t.Name) + ': USER.md ontbreekt') -ForegroundColor Red
        $failures++
        continue
    }
    if ($line -notmatch 'pleaser-behavior|zero babysitting|no pleaser') {
        Write-Host ('[FAIL] ' + $($t.Name) + ': eerste USER-regel mist trust seed') -ForegroundColor Red
        $failures++
        continue
    }
    Write-Host ('[trust-memory] ' + $t.Name + ': ' + (Format-Preview -Text $line -Max $MaxPreview)) -ForegroundColor DarkGray
}

if ($failures -gt 0) {
    Write-Host ('[FAIL] ' + 'Trust memory snapshot: ' + $failures + ' profiel(s) zonder geldige USER-regel 1') -ForegroundColor Red
    exit 1
}

if (-not $Quiet) {
    Write-Host '[OK] Trust memory USER snapshot - alle profielen' -ForegroundColor Green
}
exit 0
