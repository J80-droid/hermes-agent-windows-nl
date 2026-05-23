# Migrate legacy SOUL.md headers naar anatomy-structuur (dry-run standaard).
param(
    [string]$HermesRoot = '',
    [Alias('Profile')]
    [string]$ProfileName = '',
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

$root = if ($HermesRoot) { (Resolve-Path -LiteralPath $HermesRoot).Path } else { Get-HermesRoot }
$targets = Get-SoulTargets -HermesRoot $root
if ($ProfileName) {
    $targets = $targets | Where-Object { $_ -match "profiles\\$([regex]::Escape($ProfileName))\\SOUL\.md$" }
}

$headerMap = [ordered]@{
    '^## Tone\s' = '### Tone'
    '^## Interaction met J\.\s' = '### Interaction met J.'
    '^## Outputformaat \(institutioneel\)\s' = '### Output conventions (institutional)'
    '^## Tool governance \(domein-minimum\)\s' = '## Tool Usage'
    '^# SOUL: ' = '# SOUL.md - '
}

$legacyPatterns = @(
    '^## Advisory & trust\s',
    '^## Outputformaat \(institutioneel\)\s',
    '^## Interaction met J\.\s',
    '^## Tool governance \(domein-minimum\)\s',
    '^## Tone\s'
)

function Repair-SoulCommunicationStyleHeader {
    param([string]$Content)
    if ($Content -match '(?ms)^## Communication Style\s') { return $Content }
    if ($Content -notmatch '(?ms)^### Tone\s') { return $Content }
    return $Content -replace '(?ms)^(### Tone\s)', "## Communication Style`r`n`r`n`$1"
}

$changed = 0
foreach ($path in $targets) {
    $content = Get-SoulFileContent -Path $path
    $newContent = $content
    foreach ($key in $headerMap.Keys) {
        $newContent = $newContent -replace $key, $headerMap[$key]
    }
    $newContent = Repair-SoulCommunicationStyleHeader -Content $newContent

    $remainingLegacy = @()
    foreach ($pat in $legacyPatterns) {
        if ($newContent -match "(?m)$pat") { $remainingLegacy += $pat }
    }

    if ($newContent -ne $content) {
        $changed++
        Write-Host ('[$(if ($Apply) { 'APPLY' } else { 'DRY' })] ' + $path) -ForegroundColor $(if ($Apply) { 'Green' } else { 'Yellow' })
        if ($remainingLegacy.Count -gt 0) {
            Write-Host "  Legacy koppen over (los SYNC_SOUL_SNIPPETS.bat draaien): $($remainingLegacy -join ', ')" -ForegroundColor DarkYellow
        }
        if ($Apply) {
            $bak = "$path.backup-anatomy-$(Get-Date -Format 'yyyyMMddHHmmss')"
            Copy-Item -LiteralPath $path -Destination $bak -Force
            Set-SoulFileContent -Path $path -Content $newContent
            Write-Host "  Backup: $bak" -ForegroundColor DarkGray
        }
    }
}

Write-Host "`nResultaat: $changed bestand(en) $(if ($Apply) { 'bijgewerkt' } else { 'zouden wijzigen' })" -ForegroundColor Cyan
if (-not $Apply -and $changed -gt 0) {
    Write-Host 'Gebruik -Apply om te schrijven. Daarna: windows\SYNC_SOUL_SNIPPETS.bat -Force' -ForegroundColor Yellow
}
