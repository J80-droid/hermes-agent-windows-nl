<#
.SYNOPSIS
    Kopieert actieve API-keys van ~/.hermes/.env naar de root .env van HERMES_HOME (Windows: %LOCALAPPDATA%\hermes).
.NOTES
    Lost split-home op: User-env HERMES_HOME wijst naar Local\hermes, keys staan soms nog in ~/.hermes/.env.
#>
$ErrorActionPreference = 'Stop'

function Get-HermesRootDir {
    # Altijd root (niet profiles\<naam>) — keys horen in root .env voor provider=gemini in root config.
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    if ($env:HERMES_HOME -and (Test-Path -LiteralPath $env:HERMES_HOME)) {
        $h = (Resolve-Path -LiteralPath $env:HERMES_HOME).Path -replace '\\$', ''
        if ($h -match '\\profiles\\[^\\]+$') {
            return ($h -replace '\\profiles\\[^\\]+$', '')
        }
        return $h
    }
    return $localRoot
}

$legacyEnv = Join-Path $env:USERPROFILE '.hermes\.env'
$targetRoot = Get-HermesRootDir
$targetEnv = Join-Path $targetRoot '.env'

if (-not (Test-Path -LiteralPath $legacyEnv)) {
    Write-Host "[WARN] Geen bron: $legacyEnv" -ForegroundColor Yellow
    exit 0
}
if (-not (Test-Path -LiteralPath $targetRoot)) {
    New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
}

$keys = @('GOOGLE_API_KEY', 'GEMINI_API_KEY', 'OPENROUTER_API_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY')
$toCopy = @{}
Get-Content -LiteralPath $legacyEnv -Encoding UTF8 | ForEach-Object {
    $line = $_.TrimEnd()
    if (-not $line -or $line.StartsWith('#')) { return }
    foreach ($k in $keys) {
        if ($line -match "^\s*$k\s*=\s*(.+)\s*$") {
            $val = $Matches[1].Trim()
            if ($val -and $val -notmatch 'your_.*_here') { $toCopy[$k] = $val }
        }
    }
}

if ($toCopy.Count -eq 0) {
    Write-Host '[INFO] Geen actieve keys in ~/.hermes/.env om te kopiëren.' -ForegroundColor Cyan
    exit 0
}

if (-not (Test-Path -LiteralPath $targetEnv)) {
    Copy-Item -LiteralPath $legacyEnv -Destination $targetEnv -Force
    Write-Host "[OK] .env aangemaakt vanuit ~/.hermes -> $targetEnv" -ForegroundColor Green
    exit 0
}

$lines = [System.Collections.Generic.List[string]]::new()
if (Test-Path -LiteralPath $targetEnv) {
    $lines.AddRange([string[]](Get-Content -LiteralPath $targetEnv -Encoding UTF8))
}
foreach ($k in $toCopy.Keys) {
    $newLine = "$k=$($toCopy[$k])"
    $idx = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^\s*#?\s*$k\s*=") { $idx = $i; break }
    }
    if ($idx -ge 0) { $lines[$idx] = $newLine } else { $lines.Add($newLine) }
}
$lines | Set-Content -LiteralPath $targetEnv -Encoding UTF8
Write-Host "[OK] API-keys gesynchroniseerd naar $targetEnv ($($toCopy.Keys -join ', '))" -ForegroundColor Green
exit 0
