# Kopieer SOUL_LEGAL_DOMAIN template naar runtime; behoud Interaction-blok als dat al bestaat.
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$template = Join-Path $repoRoot 'docs\templates\SOUL_LEGAL_DOMAIN.md'
$shared = Join-Path $repoRoot 'docs\templates\SOUL_SHARED_INTERACTION.md'

$hermesRoot = Join-Path $env:LOCALAPPDATA 'hermes'
if (-not (Test-Path (Join-Path $hermesRoot 'config.yaml'))) {
    $hermesRoot = Join-Path $env:USERPROFILE '.hermes'
}
$dst = Join-Path $hermesRoot 'profiles\legal\SOUL.md'
if (-not (Test-Path -LiteralPath $template)) { throw "Template ontbreekt: $template" }

$content = (Get-Content -LiteralPath $template -Raw -Encoding UTF8).TrimEnd()
$interaction = (Get-Content -LiteralPath $shared -Raw -Encoding UTF8).Trim()
$content = $content -replace '(?ms)^## Interaction met J\.\s*\r?\n.*?(?=^## Tone)', "$interaction`r`n`r`n"
$parent = Split-Path -Parent $dst
if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
Set-Content -LiteralPath $dst -Value ($content + "`r`n") -Encoding UTF8 -NoNewline
Write-Host "[OK] $dst" -ForegroundColor Green
