# Hermes: herstel repo-onderdelen en optioneel runtime/legacy vanuit backups\backup_YYYY_MM_DD_HHMMSS\
#
# Standaard: repo_windows → windows\, repo_assets → assets\, repo_root → repo-root.
# -RestoreRuntimeFull: runtime_hermes\ → %LOCALAPPDATA%\hermes (schema v3)
# -RestoreRuntimePersonas: localappdata_hermes\ (v2) of subset uit runtime_hermes\ (v3 fallback)
# -RestoreLegacyProfile / -RestoreUserProfile: legacy_hermes\ → %USERPROFILE%\.hermes
#
# Gebruik:
#   powershell -NoProfile -ExecutionPolicy Bypass -File "windows\restore_from_backup.ps1" -BackupPath "D:\repo\backups\backup_2026_05_16_120000"
#   … -RestoreRuntimeFull

param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [switch]$RestoreUserProfile,
    [switch]$RestoreLegacyProfile,
    [switch]$RestoreRuntimePersonas,
    [switch]$RestoreRuntimeFull
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'scripts/HermesBackupCommon.ps1')

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
    Write-Host ('[ERROR] Backuppad bestaat niet: ' + $BackupPath) -ForegroundColor Red
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

$schemaVer = Get-HermesBackupSchemaVersion -BackupRoot $backupRoot
Write-Host '================================================' -ForegroundColor Cyan
Write-Host '  Hermes: herstel vanuit backup' -ForegroundColor Cyan
Write-Host '================================================' -ForegroundColor Cyan
Write-Host "  Backup:  $backupRoot" -ForegroundColor Gray
Write-Host "  Schema:  v$schemaVer" -ForegroundColor Gray
Write-Host "  Repo:    $repoRoot" -ForegroundColor Gray
Write-Host ''

Write-Host '[1/3] Repo: windows\ <- repo_windows\ ...' -ForegroundColor Gray
Invoke-HermesRobocopyMirror -Src (Join-Path $backupRoot 'repo_windows') -Dst (Join-Path $repoRoot 'windows')

Write-Host '[2/3] Repo: assets\ <- repo_assets\ ...' -ForegroundColor Gray
Invoke-HermesRobocopyMirror -Src (Join-Path $backupRoot 'repo_assets') -Dst (Join-Path $repoRoot 'assets')

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

$runtimeDst = Get-HermesRuntimeRoot

if ($RestoreRuntimeFull -or $RestoreRuntimePersonas) {
    if (-not (Test-HermesSafeForBackup -RuntimeRoot $runtimeDst)) {
        Write-Host '[ERROR] Restore geblokkeerd — stop Hermes volledig vóór runtime-restore.' -ForegroundColor Red
        exit 1
    }
}

if ($RestoreRuntimeFull) {
    $runtimeSrc = Join-Path $backupRoot 'runtime_hermes'
    if (-not (Test-Path -LiteralPath $runtimeSrc)) {
        Write-Host '[ERROR] Geen runtime_hermes\ in backup — gebruik -RestoreRuntimePersonas voor v2 subset.' -ForegroundColor Red
        exit 1
    }
    Write-Host ('[EXTRA] Volledige runtime -> ' + $runtimeDst + ' ...') -ForegroundColor Yellow
    Invoke-HermesRobocopyMirror -Src $runtimeSrc -Dst $runtimeDst -Label 'runtime restore'
}

if ($RestoreRuntimePersonas) {
    $personaRestored = $false
    $personaSubdir = Get-HermesPersonaBackupSubdir -BackupRoot $backupRoot
    $personaSrc = if ($personaSubdir) { Join-Path $backupRoot $personaSubdir } else { $null }
    if (-not $personaSrc -or -not (Test-Path -LiteralPath $personaSrc)) {
        $runtimeSubset = Join-Path $backupRoot 'runtime_hermes'
        if (Test-Path -LiteralPath $runtimeSubset) {
            Write-Host '[INFO] v3 fallback: persona-subset uit runtime_hermes\ ...' -ForegroundColor Cyan
            Write-Host ('[EXTRA] Runtime personas (subset) -> ' + $runtimeDst + ' ...') -ForegroundColor Yellow
            $n = Invoke-HermesRestorePersonaSubsetFromRuntimeBackup -RuntimeBackupRoot $runtimeSubset -RuntimeDst $runtimeDst
            Write-Host ('  [OK] ' + $n + ' persona-bestand(en) hersteld') -ForegroundColor Green
            $personaRestored = $true
        }
    }
    if (-not $personaRestored) {
        if (-not $personaSrc -or -not (Test-Path -LiteralPath $personaSrc)) {
            Write-Host '[SKIP] Geen localappdata_hermes\ of runtime_hermes\ in backup.' -ForegroundColor DarkYellow
        } else {
            Write-Host ('[EXTRA] Runtime personas -> ' + $runtimeDst + ' ...') -ForegroundColor Yellow
            $n = Invoke-HermesRestorePersonaFiles -PersonaSrc $personaSrc -RuntimeDst $runtimeDst
            Write-Host ('  [OK] ' + $n + ' persona-bestand(en) hersteld') -ForegroundColor Green
        }
    }
}

$doLegacy = $RestoreLegacyProfile -or $RestoreUserProfile
if ($doLegacy) {
    $legacyDst = Get-HermesLegacyRoot
    $legacySrc = Join-Path $backupRoot 'legacy_hermes'
    Write-Host ''
    if (Test-Path -LiteralPath $legacySrc) {
        Write-Host ('[EXTRA] legacy_hermes -> ' + $legacyDst + ' ...') -ForegroundColor Yellow
        Invoke-HermesRobocopyMirror -Src $legacySrc -Dst $legacyDst -Label 'legacy restore'
    } else {
        Write-Host '[EXTRA] Oude backup-layout: overige inhoud -> %USERPROFILE%\.hermes ...' -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $legacyDst -Force | Out-Null
        $skip = @(
            'repo_windows', 'repo_assets', 'repo_root', 'runtime_hermes', 'legacy_hermes',
            'localappdata_hermes', 'BACKUP_MANIFEST.json'
        )
        Get-ChildItem -LiteralPath $backupRoot -Force | Where-Object {
            $_.Name -notin $skip -and $_.Name -notlike '*naar taakbalk slepen.lnk'
        } | ForEach-Object {
            $target = Join-Path $legacyDst $_.Name
            if ($_.PSIsContainer) {
                Invoke-HermesRobocopyMirror -Src $_.FullName -Dst $target
            } else {
                Copy-Item -LiteralPath $_.FullName -Destination $target -Force
                Write-Host "  [OK] legacy: $($_.Name)" -ForegroundColor Green
            }
        }
    }
}

Write-Host ''
Write-Host '[OK] Herstel voltooid. Controleer git diff; draai eventueel REFRESH_TASKBAR_SHORTCUTS.bat.' -ForegroundColor Cyan
if ($RestoreRuntimeFull -or $RestoreRuntimePersonas) {
    Write-Host '[INFO] Bij display-drift: windows\APPLY_INSTITUTIONAL_RUNTIME.bat en /new in Hermes.' -ForegroundColor DarkYellow
}
exit 0
