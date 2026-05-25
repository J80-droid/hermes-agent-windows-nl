# Hermes Agent: institutioneel backup-pakket (schema v3)
#
# - runtime_hermes/     ← %LOCALAPPDATA%\hermes (canonieke runtime; bevat secrets)
# - legacy_hermes/      ← %USERPROFILE%\.hermes (_local_assets spiegel)
# - localappdata_hermes/← persona-subset (SOUL, config, memories) — v2 compat
# - repo_windows/, repo_assets/, repo_root/
# - BACKUP_MANIFEST.json (schema v3)
#
# VEREIST: Hermes/gateway volledig gestopt (Test-HermesSafeForBackup).
# Optioneel: -SkipPause of HERMES_BACKUP_NONINTERACTIVE=1
param(
    [switch]$SkipPause,
    [switch]$WhatIf
)

. (Join-Path $PSScriptRoot 'HermesShellCommon.ps1')
. (Join-HermesRepoPath -RepoRoot $PSScriptRoot -RelativePath 'scripts/HermesBackupCommon.ps1')
$ErrorActionPreference = 'Stop'

$startDir = if ($PSScriptRoot) { $PSScriptRoot } elseif ($MyInvocation.MyCommand.Path) {
    Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    (Get-Location).Path
}
$repoRoot = $null
$d = $startDir
while ($d) {
    $pp = Join-Path $d 'pyproject.toml'
    $wb = Join-Path $d 'windows\backup_hermes.ps1'
    if ((Test-Path -LiteralPath $pp) -and (Test-Path -LiteralPath $wb)) {
        $repoRoot = $d
        break
    }
    $next = Split-Path -Parent $d
    if (-not $next -or ($next -eq $d)) { break }
    $d = $next
}
if (-not $repoRoot) {
    Write-Host ('[ERROR] Geen Hermes repo gevonden (pyproject.toml + windows\backup_hermes.ps1) vanaf: ' + $startDir) -ForegroundColor Red
    exit 1
}
$repoRoot = (Resolve-Path -LiteralPath $repoRoot).Path

$runtimeRoot = Get-HermesRuntimeRoot
$legacyRoot = Get-HermesLegacyRoot
$backupRoot = Join-Path $repoRoot 'backups'
$timestamp = Get-Date -Format 'yyyy_MM_dd_HHmmss'
$backupFolder = Join-Path $backupRoot "backup_$timestamp"

Write-Host '================================================' -ForegroundColor Cyan
Write-Host '  Hermes Agent: backup (institutioneel v3)' -ForegroundColor Cyan
Write-Host '================================================' -ForegroundColor Cyan
Write-Host ('  Runtime: ' + $runtimeRoot) -ForegroundColor DarkGray
Write-Host ('  Legacy:  ' + $legacyRoot) -ForegroundColor DarkGray

if (-not (Test-HermesSafeForBackup -RuntimeRoot $runtimeRoot)) {
    exit 1
}

if (-not (Test-Path -LiteralPath $runtimeRoot)) {
    Write-Host ('[WARN] Runtime-map ontbreekt: ' + $runtimeRoot) -ForegroundColor Yellow
}

if ($WhatIf) {
    Write-Host '[INFO] WhatIf — geen bestanden gekopieerd.' -ForegroundColor Cyan
    Write-Host ('  Zou backup maken: ' + $backupFolder) -ForegroundColor DarkGray
    exit 0
}

if (-not (Test-Path $backupRoot)) { New-Item -ItemType Directory -Path $backupRoot | Out-Null }
New-Item -ItemType Directory -Path $backupFolder | Out-Null

Write-Host ('[1/12] runtime_hermes <- ' + $runtimeRoot + ' ...') -ForegroundColor Gray
$runtimeDst = Join-Path $backupFolder 'runtime_hermes'
if (Test-Path -LiteralPath $runtimeRoot) {
    Invoke-HermesRobocopyMirror -Src $runtimeRoot -Dst $runtimeDst -Label 'runtime_hermes'
} else {
    Write-Host '  [SKIP] Geen runtime-map' -ForegroundColor DarkYellow
}

Write-Host ('[2/12] legacy_hermes <- ' + $legacyRoot + ' ...') -ForegroundColor Gray
$legacyDst = Join-Path $backupFolder 'legacy_hermes'
if (Test-Path -LiteralPath $legacyRoot) {
    Invoke-HermesRobocopyMirror -Src $legacyRoot -Dst $legacyDst -Label 'legacy_hermes'
} else {
    Write-Host '  [SKIP] Geen legacy ~/.hermes' -ForegroundColor DarkYellow
}

$soulBackupPs1 = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/backup_soul_profiles.ps1'
$runtimePersonaFiles = @()
if (Test-Path -LiteralPath $soulBackupPs1) {
    Write-Host '[3/12] Persona-subset (localappdata_hermes)...' -ForegroundColor Gray
    $runtimePersonaFiles = @(& $soulBackupPs1 -BackupFolder $backupFolder)
    if ((Test-Path -LiteralPath $runtimeRoot) -and $runtimePersonaFiles.Count -eq 0) {
        Write-Host '[WARN] Runtime aanwezig maar 0 persona-bestanden gekopieerd' -ForegroundColor Yellow
    }
} else {
    Write-Host '[3/12][SKIP] backup_soul_profiles.ps1 ontbreekt' -ForegroundColor Yellow
}

Write-Host '[4/12] Repo windows\ -> repo_windows\ ...' -ForegroundColor Gray
$repoWindowsSrc = Join-Path $repoRoot 'windows'
$repoWindowsDst = Join-Path $backupFolder 'repo_windows'
if (Test-Path -LiteralPath $repoWindowsSrc) {
    Invoke-HermesRobocopyMirror -Src $repoWindowsSrc -Dst $repoWindowsDst
} else {
    Write-Host "  [SKIP] Geen map: $repoWindowsSrc" -ForegroundColor Yellow
}

Write-Host '[5/12] Repo assets\ -> repo_assets\ ...' -ForegroundColor Gray
$assetsSrc = Join-Path $repoRoot 'assets'
$assetsDst = Join-Path $backupFolder 'repo_assets'
if (Test-Path -LiteralPath $assetsSrc) {
    Invoke-HermesRobocopyMirror -Src $assetsSrc -Dst $assetsDst
} else {
    Write-Host "  [SKIP] Geen map: $assetsSrc" -ForegroundColor Yellow
}

Write-Host '[6/12] Kritieke repo-root -> repo_root\ (allowlist)...' -ForegroundColor Gray
$repoRootDst = Join-Path $backupFolder 'repo_root'
New-Item -ItemType Directory -Path $repoRootDst -Force | Out-Null
$repoRootSnapLeaves = @(
    'start_hermes.bat',
    'start_hermes_split.bat',
    'pyproject.toml',
    '.hermeslocal',
    'cli-config.yaml.example',
    '.env.example',
    'README.md',
    'README.zh-CN.md',
    'AGENTS.md',
    'CONTRIBUTING.md',
    'LICENSE',
    'SECURITY.md',
    'MANIFEST.in',
    'setup-hermes.sh',
    '.gitignore',
    '.dockerignore'
)
$copiedRepoRoot = @()
foreach ($leaf in $repoRootSnapLeaves) {
    $rf = Join-Path $repoRoot $leaf
    if (Test-Path -LiteralPath $rf) {
        Copy-Item -LiteralPath $rf -Destination (Join-Path $repoRootDst $leaf) -Force
        $copiedRepoRoot += $leaf
        Write-Host "  [OK] $leaf" -ForegroundColor DarkGray
    }
}
Get-ChildItem -LiteralPath $repoRoot -File -Filter 'RELEASE_v*.md' -ErrorAction SilentlyContinue |
    Sort-Object Name |
    ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $repoRootDst $_.Name) -Force
        $copiedRepoRoot += $_.Name
        Write-Host "  [OK] $($_.Name)" -ForegroundColor DarkGray
    }

Write-Host '[7/12] BACKUP_MANIFEST.json (schema v3)...' -ForegroundColor Gray
$displaySnapshot = Get-HermesInstitutionalDisplaySnapshot -RuntimeRoot $runtimeRoot
$runtimeFileCount = 0
if (Test-Path -LiteralPath $runtimeDst) {
    $runtimeFileCount = @(Get-ChildItem -LiteralPath $runtimeDst -Recurse -File -ErrorAction SilentlyContinue).Count
}
$personaSoulCount = 0
$personaDir = Join-Path $backupFolder 'localappdata_hermes'
if (Test-Path -LiteralPath $personaDir) {
    $personaSoulCount = @(Get-ChildItem -LiteralPath $personaDir -Recurse -Filter 'SOUL.md' -File -ErrorAction SilentlyContinue).Count
}
$manifest = [ordered]@{
    schema_version               = 3
    format                       = 'hermes_windows_backup'
    created_utc                  = (Get-Date).ToUniversalTime().ToString('o')
    hostname                     = $env:COMPUTERNAME
    windows_user                 = $env:USERNAME
    repo_root                    = $repoRoot
    hermes_runtime_home          = $runtimeRoot
    hermes_legacy_home           = $legacyRoot
    backup_folder                = $backupFolder
    contains_secrets             = $true
    runtime_file_count           = $runtimeFileCount
    persona_file_count           = @($runtimePersonaFiles).Count
    persona_soul_count           = $personaSoulCount
    repo_root_files              = $copiedRepoRoot
    institutional_display_snapshot = $displaySnapshot
    includes                     = @(
        'runtime_hermes',
        'legacy_hermes',
        'localappdata_hermes',
        'repo_windows',
        'repo_assets',
        'repo_root',
        'taskbar_shortcuts_in_backup_root',
        'BACKUP_MANIFEST'
    )
    runtime_personas             = [ordered]@{
        backup_subdir = 'localappdata_hermes'
        files         = @($runtimePersonaFiles)
    }
}
$manifestPath = Join-Path $backupFolder 'BACKUP_MANIFEST.json'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Host "  -> $manifestPath" -ForegroundColor DarkGray

Write-Host '[8/12] Taakbalk-.lnk in backup-map ...' -ForegroundColor Gray
$taskbarPs1 = Join-Path $repoRoot 'windows\create_taskbar_shortcuts.ps1'
if (Test-Path -LiteralPath $taskbarPs1) {
    & $taskbarPs1 -RepoRoot $repoRoot -OutDir $backupFolder
} else {
    Write-Host "  [SKIP] create_taskbar_shortcuts.ps1 niet gevonden" -ForegroundColor Yellow
}

Write-Host '[9/12] SQLite-integriteit (runtime_hermes/state.db)...' -ForegroundColor Gray
$dbPath = Join-Path $runtimeDst 'state.db'
if (Test-Path -LiteralPath $dbPath) {
    $verifyCmd = "import sqlite3; conn = sqlite3.connect(r'$dbPath'); res = conn.execute('PRAGMA integrity_check').fetchone(); print(res[0])"
    $res = $null
    $prevE = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $res = py -3 -c $verifyCmd 2>$null
    }
    if (-not $res) {
        . (Join-Path $PSScriptRoot 'HermesPythonPolicy.ps1')
        $condaPy = Resolve-HermesPythonExe -RepoRoot $repo -RequirePip
        if ($condaPy) {
            $res = & $condaPy -c $verifyCmd 2>$null
        }
    }
    $ErrorActionPreference = $prevE
    if ($res -eq 'ok') {
        Write-Host '[OK] state.db: integrity_check ok.' -ForegroundColor Green
    } else {
        Write-Host ('[WARN] Database check: ' + $res) -ForegroundColor Yellow
    }
} else {
    Write-Host '[INFO] Geen state.db in runtime_hermes.' -ForegroundColor Gray
}

Write-Host '[10/12] Taakbalk-.lnk in repo windows\ vernieuwen ...' -ForegroundColor Gray
$winDir = Join-Path $repoRoot 'windows'
if (Test-Path -LiteralPath $taskbarPs1) {
    & $taskbarPs1 -RepoRoot $repoRoot -OutDir $winDir -Quiet
}

Write-Host ('[11/12] Sync naar ' + $legacyRoot + '\_local_assets ...') -ForegroundColor Gray
$syncScript = Join-Path $repoRoot 'windows\sync_local_assets_to_backup.ps1'
if (Test-Path -LiteralPath $syncScript) {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $syncScript
        if (Test-NativeCommandFailed) {
            Write-Host ('[WARN] sync_local_assets_to_backup.ps1 exit ' + $LASTEXITCODE) -ForegroundColor Yellow
        }
    } catch {
        Write-Host ('[WARN] Sync mislukt: ' + $($_.Exception.Message)) -ForegroundColor Yellow
    } finally {
        $ErrorActionPreference = $prevEap
    }
} else {
    Write-Host ('[WARN] sync_local_assets_to_backup.ps1 niet gevonden') -ForegroundColor Yellow
}

Write-Host '[12/12] Post-backup verify + script-keten ...' -ForegroundColor Gray
$post = Test-HermesBackupPostVerify -BackupFolder $backupFolder -Strict
if ($post.Ok) {
    Write-Host '[OK] Post-backup verify PASS' -ForegroundColor Green
} else {
    foreach ($issue in $post.Issues) {
        Write-Host ('[WARN] ' + $issue) -ForegroundColor Yellow
    }
}

$verifyScript = Join-Path $repoRoot 'windows\verify_windows_script_chain.ps1'
if (Test-Path -LiteralPath $verifyScript) {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $verifyScript -RepoRoot $repoRoot
        if (Test-NativeCommandFailed) {
            Write-Host '[WARN] verify_windows_script_chain: keten incompleet' -ForegroundColor Yellow
        }
    } catch {
        Write-Host ('[WARN] Verify mislukt: ' + $($_.Exception.Message)) -ForegroundColor Yellow
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

Write-Host ('[OK] Backup voltooid: ' + $backupFolder) -ForegroundColor Green
Write-Host '[INFO] Bevat secrets (.env, auth) — niet delen buiten vertrouwde DR.' -ForegroundColor DarkYellow

Write-Host ''
$nonInteractive = $SkipPause -or ($env:HERMES_BACKUP_NONINTERACTIVE -in @('1', 'true', 'True', 'yes', 'Yes'))
if (-not $nonInteractive) {
    pause
}
