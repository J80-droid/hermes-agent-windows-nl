# Kopieer SOUL_LEGAL_DOMAIN template naar runtime; injecteer Interaction + Outputformaat uit shared templates.
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$template = Join-Path $repoRoot 'docs\templates\SOUL_LEGAL_DOMAIN.md'
$sharedInteraction = Join-Path $repoRoot 'docs\templates\SOUL_SHARED_INTERACTION.md'
$sharedOutput = Join-Path $repoRoot 'docs\templates\SOUL_SHARED_OUTPUT_FORMAT.md'

$hermesRoot = Join-Path $env:LOCALAPPDATA 'hermes'
if (-not (Test-Path (Join-Path $hermesRoot 'config.yaml'))) {
    $hermesRoot = Join-Path $env:USERPROFILE '.hermes'
}
$dst = Join-Path $hermesRoot 'profiles\legal\SOUL.md'
if (-not (Test-Path -LiteralPath $template)) { throw "Template ontbreekt: $template" }

$content = (Get-Content -LiteralPath $template -Raw -Encoding UTF8).TrimEnd()
$interaction = (Get-Content -LiteralPath $sharedInteraction -Raw -Encoding UTF8).Trim()
$output = (Get-Content -LiteralPath $sharedOutput -Raw -Encoding UTF8).Trim()

$content = $content -replace '(?ms)^## Outputformaat \(institutioneel\)\s*\r?\n.*?(?=^## )', "$output`r`n`r`n"
$content = $content -replace '(?ms)^## Interaction met J\.\s*\r?\n.*?(?=^## Tone)', "$interaction`r`n`r`n"

$parent = Split-Path -Parent $dst
if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
Set-Content -LiteralPath $dst -Value ($content + "`r`n") -Encoding UTF8 -NoNewline
Write-Host "[OK] $dst (legal + shared Interaction + Outputformaat)" -ForegroundColor Green
