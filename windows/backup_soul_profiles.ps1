# Backup runtime persona files from %LOCALAPPDATA%\hermes (SOUL, active_profile).
param(
    [Parameter(Mandatory)][string]$BackupFolder
)

$ErrorActionPreference = 'Stop'

function Get-HermesRoot {
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

$copiedFiles = [System.Collections.Generic.List[string]]::new()

function Copy-HermesPersonaFile {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$RelPath,
        [Parameter(Mandatory)][string]$DstRoot
    )
    $src = Join-Path $Root $RelPath
    if (-not (Test-Path -LiteralPath $src)) { return }
    $dst = Join-Path $DstRoot $RelPath
    $parent = Split-Path -Parent $dst
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Copy-Item -LiteralPath $src -Destination $dst -Force
    [void]$script:copiedFiles.Add(($RelPath -replace '\\', '/'))
}

$root = Get-HermesRoot
if (-not (Test-Path -LiteralPath (Join-Path $root 'config.yaml'))) {
    Write-Host "[SKIP] Geen Hermes runtime home: $root" -ForegroundColor Yellow
    return @()
}

$dstRoot = Join-Path $BackupFolder 'localappdata_hermes'
New-Item -ItemType Directory -Path $dstRoot -Force | Out-Null

Copy-HermesPersonaFile -Root $root -RelPath 'SOUL.md' -DstRoot $dstRoot
Copy-HermesPersonaFile -Root $root -RelPath 'active_profile' -DstRoot $dstRoot

$kanban = 'profiles/core/KANBAN_WORKFLOWS.md'
Copy-HermesPersonaFile -Root $root -RelPath $kanban -DstRoot $dstRoot

$profilesDir = Join-Path $root 'profiles'
if (Test-Path -LiteralPath $profilesDir) {
    Get-ChildItem -LiteralPath $profilesDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $rel = "profiles/$($_.Name)/SOUL.md"
        Copy-HermesPersonaFile -Root $root -RelPath $rel -DstRoot $dstRoot
    }
}

Write-Host "  [OK] Runtime personas: $($copiedFiles.Count) bestand(en) -> localappdata_hermes\" -ForegroundColor DarkGray
return $copiedFiles.ToArray()
