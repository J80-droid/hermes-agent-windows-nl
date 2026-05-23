# Kopieer SOUL_*_DOMAIN.md (of core orchestrator) naar runtime profiles/<naam>/SOUL.md
param(
    [Parameter(Mandatory)][string]$Profile,
    [string]$RepoRoot = '',
    [string]$HermesRoot = ''
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$templateName = switch ($Profile) {
    'core' { 'SOUL_CORE_ORCHESTRATOR.md' }
    default {
        $candidate = "SOUL_$($Profile.ToUpper())_DOMAIN.md"
        if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "docs\templates\$candidate"))) {
            throw "Template ontbreekt voor profiel '$Profile': docs\templates\$candidate"
        }
        $candidate
    }
}
$template = Join-Path $RepoRoot "docs\templates\$templateName"
if (-not (Test-Path -LiteralPath $template)) {
    throw "Template ontbreekt: $template"
}

$root = if ($HermesRoot) { (Resolve-Path -LiteralPath $HermesRoot).Path } else { Get-HermesRoot }
$dst = Join-Path $root "profiles\$Profile\SOUL.md"
$parent = Split-Path -Parent $dst
if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}

$content = (Get-SoulFileContent -Path $template).TrimEnd()
Set-SoulFileContent -Path $dst -Content ($content + "`r`n")
Write-Host "[OK] $dst <= $templateName" -ForegroundColor Green
Write-Host '[TIP] Draai windows\SYNC_SOUL_SNIPPETS.bat -Force voor shared anatomy-blokken.' -ForegroundColor DarkYellow
exit 0
