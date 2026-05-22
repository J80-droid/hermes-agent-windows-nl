# Sync ## Tool governance (domein-minimum) from repo template into all profile SOUL.md files.
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
    if ($HermesRoot) { return (Resolve-Path -LiteralPath $HermesRoot).Path }
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

$templatePath = Join-Path $RepoRoot 'docs/templates/SOUL_SHARED_TOOL_GOVERNANCE.md'
if (-not (Test-Path -LiteralPath $templatePath)) {
    Write-Error "Template ontbreekt: $templatePath"
}

$snippet = (Get-Content -LiteralPath $templatePath -Raw -Encoding UTF8).Trim()
$root = Get-HermesRoot

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

$marker = '## Tool governance (domein-minimum)'
$updated = 0
foreach ($path in $targets) {
    $content = Get-Content -LiteralPath $path -Raw -Encoding UTF8
    if ($content -match '(?ms)^## Tool governance \(domein-minimum\)\s*\r?\n.*?(?=^\#\# |\z)') {
        $newContent = $content -replace '(?ms)^## Tool governance \(domein-minimum\)\s*\r?\n.*?(?=^\#\# |\z)', "$snippet`r`n`r`n"
    } elseif ($content -match '(?ms)^## Advisory & trust\s*\r?\n') {
        $newContent = $content -replace '(?ms)^(## Advisory & trust\s*\r?\n)', "$snippet`r`n`r`n`$1"
    } elseif ($content -match '(?ms)^## Interaction met J\.\s*\r?\n') {
        $newContent = $content -replace '(?ms)^(## Interaction met J\.\s*\r?\n)', "$snippet`r`n`r`n`$1"
    } else {
        $newContent = $content.TrimEnd() + "`r`n`r`n" + $snippet + "`r`n"
    }
    if ($newContent -ne $content) {
        Set-Content -LiteralPath $path -Value $newContent -Encoding UTF8 -NoNewline
        $updated++
        Write-Host "[OK] $path" -ForegroundColor Green
    }
}
Write-Host "[INFO] Tool governance bijgewerkt: $updated SOUL-bestand(en)" -ForegroundColor Cyan
