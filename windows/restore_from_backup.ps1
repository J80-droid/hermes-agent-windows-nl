# Hermes: herstel repo-onderdelen (en optioneel ~/.hermes) vanuit backups\backup_YYYY_MM_DD_HHMMSS\
#
# Standaard alleen repo: repo_windows → windows\, repo_assets → assets\, repo_root → repo-root.
# Disaster recovery: -RestoreUserProfile kopieert alle overige inhoud van de backup naar %USERPROFILE%\.hermes
# (overschrijft bestaande Hermes-data — alleen gebruiken als je weet wat je doet).
#
# Gebruik:
#   powershell -NoProfile -ExecutionPolicy Bypass -File "windows\restore_from_backup.ps1" -BackupPath "D:\repo\hermes-agent\backups\backup_2026_05_16_120000"
#   … -RestoreUserProfile

param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [switch]$RestoreUserProfile,
    [switch]$RestoreRuntimePersonas
)

$ErrorActionPreference = 'Stop'

function Get-HermesRepoRootFromScript {
    $startDir = if ($PSScriptRoot) { $PSScriptRoot } elseif ($MyInvocation.MyCommand.Path) {
        Split-Path -Parent $MyInvocation.MyCommand.Path
    } else {
        (Get-Location).Path
    }
    $d = $startDir
    while ($d) {
        $pp = Join-Path $d 'pyproject.toml'
        $wb = Join-Path $d 'windows\backup_hermes.ps1'
        if ((Test-Path -LiteralPath $pp) -and (Test-Path -LiteralPath $wb)) {
            return (Resolve-Path -LiteralPath $d).Path
        }
        $next = Split-Path -Parent $d
        if (-not $next -or ($next -eq $d)) { break }
        $d = $next
    }
    return $null
}

$repoRoot = Get-HermesRepoRootFromScript
if (-not $repoRoot) {
    Write-Host '[ERROR] Geen repo-root gevonden (pyproject.toml + windows\backup_hermes.ps1).' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $BackupPath)) {
    Write-Host ('[ERROR] ' + 'Backuppad bestaat niet: ' + $BackupPath) -ForegroundColor Red
    exit 1
}
$backupRoot = (Resolve-Path -LiteralPath $BackupPath).Path

$manifestPath = Join-Path $backupRoot 'BACKUP_MANIFEST.json'
if (-not (Test-Path -LiteralPath $manifestPath)) {
    $legacy = (Test-Path -LiteralPath (Join-Path $backupRoot 'repo_windows'))
    if (-not $legacy) {
        Write-Host '[ERROR] Geen BACKUP_MANIFEST.json en geen repo_windows\ — dit lijkt geen Hermes-backupmap.' -ForegroundColor Red
        exit 1
    }
    Write-Host '[WARN] Geen BACKUP_MANIFEST.json (oude backup) — ga door op basis van repo_windows\.' -ForegroundColor Yellow
}

Write-Host '================================================' -ForegroundColor Cyan
Write-Host '  Hermes: herstel vanuit backup' -ForegroundColor Cyan
Write-Host '================================================' -ForegroundColor Cyan
Write-Host "  Backup: $backupRoot" -ForegroundColor Gray
Write-Host "  Repo:   $repoRoot" -ForegroundColor Gray
Write-Host ''

function Get-HermesRobocopyExePath {
    $windir = if ($env:SystemRoot) { $env:SystemRoot } else { $env:WINDIR }
    foreach ($tail in @('System32\robocopy.exe', 'Sysnative\System32\robocopy.exe')) {
        $p = Join-Path $windir $tail
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $null
}

$robocopy = Get-HermesRobocopyExePath

function Invoke-HermesRobocopyRestore {
    param(
        [Parameter(Mandatory)][string]$Src,
        [Parameter(Mandatory)][string]$Dst
    )
    if (-not (Test-Path -LiteralPath $Src)) {
        Write-Host "  [SKIP] Bron ontbreekt: $Src" -ForegroundColor DarkYellow
        return
    }
    New-Item -ItemType Directory -Path $Dst -Force | Out-Null
    if ($robocopy -and (Test-Path -LiteralPath $robocopy)) {
        # Zelfde robocopy-basis als backup_hermes.ps1: /COPY:DT + *.log uit + docker home\.cache XD
        # (bron kan profiel-spiegel zijn: ...\sandboxes\docker\… of alleen map ...\sandboxes met child docker\).
        $srcN = $Src.TrimEnd('\', '/')
        $xdDirs = [System.Collections.Generic.List[string]]::new()
        $sdDocker = Join-Path $srcN 'sandboxes\docker'
        $dockerUnderSandboxesRoot = Join-Path $srcN 'docker'
        if (Test-Path -LiteralPath $sdDocker) {
            [void]$xdDirs.Add('sandboxes\docker\default\home\.cache')
            Get-ChildItem -LiteralPath $sdDocker -Directory -ErrorAction SilentlyContinue | ForEach-Object {
                $homeCache = Join-Path $_.FullName 'home\.cache'
                if (Test-Path -LiteralPath $homeCache) {
                    [void]$xdDirs.Add([System.IO.Path]::GetFullPath($homeCache))
                }
            }
        } elseif (Test-Path -LiteralPath $dockerUnderSandboxesRoot) {
            [void]$xdDirs.Add('docker\default\home\.cache')
            Get-ChildItem -LiteralPath $dockerUnderSandboxesRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
                $homeCache = Join-Path $_.FullName 'home\.cache'
                if (Test-Path -LiteralPath $homeCache) {
                    [void]$xdDirs.Add([System.IO.Path]::GetFullPath($homeCache))
                }
            }
        }
        [void]$xdDirs.Add('__pycache__')
        $xdUnique = @($xdDirs | Select-Object -Unique)
        $rcArgs = @(
            $srcN, $Dst, '/E', '/COPY:DT', '/XF', '*.log',
            '/R:1', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP'
        )
        if ($xdUnique.Count -gt 0) {
            $rcArgs += '/XD'
            $rcArgs += $xdUnique
        }
        & $robocopy @rcArgs
        $rc = $LASTEXITCODE
        if ($rc -ge 8) {
            throw "robocopy eindigde met $rc ($Src -> $Dst)"
        }
        Write-Host "  [OK] $Src -> $Dst" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Geen robocopy.exe — fallback Copy-Item (top-level uitsluiting lsp/cache/__pycache__)." -ForegroundColor Yellow
        $skipNames = [System.Collections.Generic.HashSet[string]]::new([string[]]@('lsp', 'cache', '__pycache__'))
        Get-ChildItem -LiteralPath $Src -Force | ForEach-Object {
            if ($skipNames.Contains($_.Name)) { return }
            $t = Join-Path $Dst $_.Name
            Copy-Item -LiteralPath $_.FullName -Destination $t -Recurse -Force
        }
        Write-Host "  [OK] Copy-Item (geen robocopy): $Src -> $Dst" -ForegroundColor Green
    }
}

Write-Host '[1/3] Repo: windows\ <- repo_windows\ ...' -ForegroundColor Gray
Invoke-HermesRobocopyRestore -Src (Join-Path $backupRoot 'repo_windows') -Dst (Join-Path $repoRoot 'windows')

Write-Host '[2/3] Repo: assets\ <- repo_assets\ ...' -ForegroundColor Gray
Invoke-HermesRobocopyRestore -Src (Join-Path $backupRoot 'repo_assets') -Dst (Join-Path $repoRoot 'assets')

Write-Host '[3/3] Repo-rootbestanden <- repo_root\ ...' -ForegroundColor Gray
$rr = Join-Path $backupRoot 'repo_root'
if (Test-Path -LiteralPath $rr) {
    Get-ChildItem -LiteralPath $rr -File | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $repoRoot $_.Name) -Force
        Write-Host "  [OK] $($_.Name)" -ForegroundColor Green
    }
} else {
    Write-Host '  [SKIP] Geen repo_root\' -ForegroundColor DarkYellow
}

function Get-HermesRuntimeRoot {
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

if ($RestoreRuntimePersonas) {
    $personaSrc = Join-Path $backupRoot 'localappdata_hermes'
    if (-not (Test-Path -LiteralPath $personaSrc)) {
        Write-Host '[SKIP] Geen localappdata_hermes\ in backup (schema v2).' -ForegroundColor DarkYellow
    } else {
        $runtimeDst = Get-HermesRuntimeRoot
        Write-Host ('[EXTRA] ' + 'Runtime personas -> ' + $runtimeDst + ' ...') -ForegroundColor Yellow
        Get-ChildItem -LiteralPath $personaSrc -Recurse -File | ForEach-Object {
            $rel = $_.FullName.Substring($personaSrc.Length).TrimStart('\')
            $target = Join-Path $runtimeDst $rel
            $parent = Split-Path -Parent $target
            if ($parent -and -not (Test-Path -LiteralPath $parent)) {
                New-Item -ItemType Directory -Path $parent -Force | Out-Null
            }
            Copy-Item -LiteralPath $_.FullName -Destination $target -Force
            Write-Host "  [OK] $rel" -ForegroundColor Green
        }
    }
}

if ($RestoreUserProfile) {
    Write-Host ''
    Write-Host '[EXTRA] %USERPROFILE%\.hermes <- overige backup-inhoud (geen repo_* / manifest / taakbalk-.lnk) ...' -ForegroundColor Yellow
    $hermesDst = Join-Path $env:USERPROFILE '.hermes'
    New-Item -ItemType Directory -Path $hermesDst -Force | Out-Null
    $skip = @('repo_windows', 'repo_assets', 'repo_root', 'BACKUP_MANIFEST.json')
    Get-ChildItem -LiteralPath $backupRoot -Force | Where-Object {
        $_.Name -notin $skip -and $_.Name -notlike '*naar taakbalk slepen.lnk'
    } | ForEach-Object {
        $target = Join-Path $hermesDst $_.Name
        if ($_.PSIsContainer) {
            Invoke-HermesRobocopyRestore -Src $_.FullName -Dst $target
        } else {
            Copy-Item -LiteralPath $_.FullName -Destination $target -Force
            Write-Host "  [OK] user: $($_.Name)" -ForegroundColor Green
        }
    }
}

Write-Host ''
Write-Host '[OK] Herstelrepo-acties voltooid. Controleer git diff; draai eventueel REFRESH_TASKBAR_SHORTCUTS.bat.' -ForegroundColor Cyan
exit 0
