# Kopieer SOUL_*_DOMAIN.md (of core orchestrator) naar runtime profiles/<naam>/SOUL.md
param(
    [Parameter(Mandatory)]
    [Alias('Profile')]
    [string]$ProfileName,
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$SuppressTip
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$allowed = Get-DomainSoulProfileNames
if ($ProfileName -notin $allowed) {
    throw "Profiel '$ProfileName' is geen domein in domain_toolsets.yaml. Toegestaan: $($allowed -join ', ')"
}

$templateName = switch ($ProfileName) {
    'core' { 'SOUL_CORE_ORCHESTRATOR.md' }
    default {
        $candidate = "SOUL_$($ProfileName.ToUpper())_DOMAIN.md"
        if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "docs\templates\$candidate"))) {
            throw "Template ontbreekt voor profiel '$ProfileName': docs\templates\$candidate"
        }
        $candidate
    }
}
$template = Join-Path $RepoRoot "docs\templates\$templateName"
if (-not (Test-Path -LiteralPath $template)) {
    throw "Template ontbreekt: $template"
}

$root = if ($HermesRoot) { (Resolve-Path -LiteralPath $HermesRoot).Path } else { Get-HermesRoot }
$dst = Join-Path $root "profiles\$ProfileName\SOUL.md"
$parent = Split-Path -Parent $dst
if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}

$content = (Get-SoulFileContent -Path $template).TrimEnd()
Set-SoulFileContent -Path $dst -Content ($content + "`r`n")
Write-Host ('[OK] ' + $dst + ' <= ' + $templateName) -ForegroundColor Green
if (-not $SuppressTip) {
    Write-Host '[TIP] Draai windows\SYNC_SOUL_SNIPPETS.bat -Force voor shared anatomy-blokken.' -ForegroundColor DarkYellow
}
exit 0
