# Sync ## Outputformaat (institutioneel) from repo template into all profile SOUL.md files.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = ''
)

$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

function Get-HermesRoot {
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

$templatePath = Join-Path $RepoRoot 'docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md'
if (-not (Test-Path -LiteralPath $templatePath)) {
    Write-Error "Template ontbreekt: $templatePath"
}

$snippet = (Get-Content -LiteralPath $templatePath -Raw -Encoding UTF8).Trim()
$root = if ($HermesRoot) { (Resolve-Path -LiteralPath $HermesRoot).Path } else { Get-HermesRoot }

$targets = @()
$rootSoul = Join-Path $root 'SOUL.md'
if (Test-Path -LiteralPath $rootSoul) { $targets += $rootSoul }
$profilesDir = Join-Path $root 'profiles'
if (Test-Path -LiteralPath $profilesDir) {
    Get-ChildItem -LiteralPath $profilesDir -Directory | ForEach-Object {
        $p = Join-Path $_.FullName 'SOUL.md'
        if (Test-Path -LiteralPath $p) { $targets += $p }
    }
}

$updated = 0
foreach ($path in $targets) {
    $content = Get-Content -LiteralPath $path -Raw -Encoding UTF8
    if ($content -match '(?ms)^## Outputformaat \(institutioneel\)\s*\r?\n.*?(?=^\#\# |\z)') {
        $newContent = $content -replace '(?ms)^## Outputformaat \(institutioneel\)\s*\r?\n.*?(?=^\#\# |\z)', "$snippet`r`n`r`n"
    } elseif ($content -match '(?ms)^## Interaction met J\.\s*\r?\n') {
        $newContent = $content -replace '(?ms)^(## Interaction met J\.\s*\r?\n)', "$snippet`r`n`r`n`$1"
    } elseif ($content -match '(?ms)^## Tone\s') {
        $newContent = $content -replace '(?ms)^(## Tone\s)', "$snippet`r`n`r`n`$1"
    } else {
        $newContent = $content.TrimEnd() + "`r`n`r`n" + $snippet + "`r`n"
    }
    if ($newContent -ne $content) {
        Set-Content -LiteralPath $path -Value $newContent -Encoding UTF8 -NoNewline
        $updated++
        Write-Host "[OK] $path" -ForegroundColor Green
    }
}
Write-Host "[INFO] Output-formaat bijgewerkt: $updated SOUL-bestand(en)" -ForegroundColor Cyan
