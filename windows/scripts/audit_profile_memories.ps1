# Rapport per profiel: MEMORY/USER lengte, encoding, duplicaten, identiteitslek.
param(
    [string]$HermesRoot = '',
    [switch]$FixEncoding
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MemoryAuditCommon.ps1')

if (-not $HermesRoot) {
    $HermesRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (-not (Test-Path -LiteralPath (Join-Path $HermesRoot 'config.yaml'))) {
        $HermesRoot = Join-Path $env:USERPROFILE '.hermes'
    }
}

$issues = 0
$profilesDir = Join-Path $HermesRoot 'profiles'
if (-not (Test-Path -LiteralPath $profilesDir)) {
    Write-Host "[FAIL] profiles map ontbreekt: $profilesDir" -ForegroundColor Red
    exit 1
}

Write-Host "=== Audit profile memories ===" -ForegroundColor Cyan
Write-Host "Hermes root: $HermesRoot"
Write-Host ''

Get-ChildItem -LiteralPath $profilesDir -Directory | Sort-Object Name | ForEach-Object {
    $name = $_.Name
    $cfg = Join-Path $_.FullName 'config.yaml'
    $lim = Get-MemoryLimitsFromConfig -ConfigPath $cfg
    $memLimit = if ($lim.MemoryCharLimit -gt 0) { $lim.MemoryCharLimit } else { 4000 }
    $userLimit = if ($lim.UserCharLimit -gt 0) { $lim.UserCharLimit } else { 1800 }

    Write-Host "--- $name ---" -ForegroundColor Cyan
    foreach ($file in @('MEMORY.md', 'USER.md')) {
        $path = Join-Path $_.FullName "memories\$file"
        if (-not (Test-Path -LiteralPath $path)) {
            Write-Host "  [WARN] $file ontbreekt" -ForegroundColor Yellow
            continue
        }
        $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8
        $len = $raw.Length
        $cap = if ($file -eq 'MEMORY.md') { $memLimit } else { $userLimit }
        $status = if ($len -le $cap) { 'OK' } else { 'OVER' }
        $color = if ($len -le $cap) { 'Green' } else { 'Red' }
        if ($len -gt $cap) { $script:issues++ }
        Write-Host "  [$status] $file : $len / $cap" -ForegroundColor $color

        if (Test-MemoryDoubleEncoding -Text $raw) {
            Write-Host '  [FAIL] double-encoding section marker' -ForegroundColor Red
            $script:issues++
            if ($FixEncoding) {
                $bad = Get-MemoryDoubleEncodedSectionMarker
                $good = Get-MemorySectionMarker
                $fixed = $raw.Replace($bad, $good)
                $fixed | Set-Content -LiteralPath $path -Encoding UTF8 -NoNewline
                Write-Host '  [FIX] section marker encoding gecorrigeerd' -ForegroundColor Yellow
            }
        }

        $leaks = $null
        if (Test-MemoryFileIdentityLeaks -FilePath $path -LeakLines ([ref]$leaks)) {
            Write-Host "  [FAIL] identiteitslek ($($leaks.Count) regel(s))" -ForegroundColor Red
            $script:issues++
        }

        if ($file -eq 'MEMORY.md') {
            $dups = Get-DuplicateMemorySections -FilePath $path
            if ($dups.Count -gt 0) {
                Write-Host "  [WARN] dubbele §-secties: $($dups.Count)" -ForegroundColor Yellow
                foreach ($d in $dups | Select-Object -First 2) {
                    Write-Host "         $d" -ForegroundColor DarkYellow
                }
            }
        }
    }
    Write-Host ''
}

if ($issues -gt 0) {
    Write-Host "=== AUDIT: $issues issue(s) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== AUDIT: PASS ===' -ForegroundColor Green
exit 0
