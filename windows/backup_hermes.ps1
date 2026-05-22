# Hermes Agent: institutioneel backup-pakket (user data + repo-snapshot + manifest)
# - %USERPROFILE%\.hermes → backupmap (robocopy, *.log overal uitgesloten; /XD lsp, cache,
#   __pycache__ op profiel — LSP-binaries zijn vaak symlinks/junctions → robocopy ERROR 3)
# - Repo windows\     → backupmap\repo_windows\
# - Repo assets\      → backupmap\repo_assets\   (branding / Hermes_logo.png)
# - Kritieke repo-rootbestanden → backupmap\repo_root\ (allowlist + RELEASE_v*.md; geen live secrets)
# - BACKUP_MANIFEST.json (schema, tijdstip, machine — audit trail)
# - Taakbalk-.lnk in backup-root + SQLite-check + sync _local_assets
#
# Optioneel: -SkipPause of omgeving HERMES_BACKUP_NONINTERACTIVE=1 om "Press any key" over te slaan (CI/automation).
param(
    [switch]$SkipPause
)
$ErrorActionPreference = "Stop"

$hermesSource = "$env:USERPROFILE\.hermes"
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
    Write-Host "[ERROR] Geen Hermes repo gevonden (pyproject.toml + windows\backup_hermes.ps1) vanaf: $startDir" -ForegroundColor Red
    exit 1
}
$repoRoot = (Resolve-Path -LiteralPath $repoRoot).Path

$backupRoot = Join-Path $repoRoot "backups"
$timestamp = Get-Date -Format "yyyy_MM_dd_HHmmss"
$backupFolder = Join-Path $backupRoot "backup_$timestamp"

function Get-HermesRobocopyExePath {
    # WOW64: 32-bit PowerShell ziet System32 als SysWOW64 — Sysnative leidt naar echte 64-bit robocopy.
    $windir = if ($env:SystemRoot) { $env:SystemRoot } else { $env:WINDIR }
    foreach ($tail in @('System32\robocopy.exe', 'Sysnative\System32\robocopy.exe')) {
        $p = Join-Path $windir $tail
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $null
}

$robocopyExe = Get-HermesRobocopyExePath

function Invoke-HermesRobocopyBackup {
    param(
        [Parameter(Mandatory)][string]$Src,
        [Parameter(Mandatory)][string]$Dst
    )
    if (-not (Test-Path -LiteralPath $Src)) {
        Write-Host "  [SKIP] Bron ontbreekt: $Src" -ForegroundColor DarkYellow
        return
    }
    New-Item -ItemType Directory -Path $Dst -Force | Out-Null
    if ($robocopyExe -and (Test-Path -LiteralPath $robocopyExe)) {
        # /E alle submappen; /XF *.log sluit .log overal uit (PowerShell Copy-Item -Exclude doet dat niet betrouwbaar recursief)
        # /COPY:DT = data + tijdstempels, géén attributen — voorkomt ERROR 1920 / "geen toegang" op door Docker/UV
        #   vergrendelde bestanden onder sandboxes\...\home\.cache\uv (attribuut-reset faalt).
        # /XD: uv/pip-cache onder elke docker-sandbox-workspace (…\sandboxes\docker\<ws>\home\.cache).
        #   Geen wildcards — oudere robocopy geeft dan "Invalid Parameter" (exit 16). Wel vaste relatieve
        #   default + alle bestaande absolute paden die we onder sandboxes\docker\ vinden.
        $srcN = $Src.TrimEnd('\', '/')
        $xdDirs = [System.Collections.Generic.List[string]]::new()
        [void]$xdDirs.Add('sandboxes\docker\default\home\.cache')
        $dockerRoot = Join-Path $srcN 'sandboxes\docker'
        if (Test-Path -LiteralPath $dockerRoot) {
            Get-ChildItem -LiteralPath $dockerRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
                $homeCache = Join-Path $_.FullName 'home\.cache'
                if (Test-Path -LiteralPath $homeCache) {
                    [void]$xdDirs.Add([System.IO.Path]::GetFullPath($homeCache))
                }
            }
        }
        # Profiel: geen LSP/npm-cache of Python bytecode — symlinks + ERROR 3 / eindeloze retries
        $hermesNorm = [System.IO.Path]::GetFullPath($hermesSource.TrimEnd('\', '/'))
        $srcNorm = [System.IO.Path]::GetFullPath($srcN)
        if ($srcNorm -eq $hermesNorm) {
            [void]$xdDirs.Add('lsp')
            [void]$xdDirs.Add('cache')
        }
        [void]$xdDirs.Add('__pycache__')
        $xdUnique = $xdDirs | Select-Object -Unique
        $rcArgs = @(
            $srcN, $Dst, '/E', '/COPY:DT', '/XF', '*.log',
            '/R:1', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP',
            '/XD'
        ) + @($xdUnique)
        & $robocopyExe @rcArgs
        $rc = $LASTEXITCODE
        if ($rc -ge 8) {
            throw "robocopy eindigde met foutcode $rc ($Src -> $Dst)"
        }
        Write-Host "  [OK] robocopy -> $Dst" -ForegroundColor DarkGray
    } else {
        Write-Host "  [WARN] Geen robocopy.exe — fallback Copy-Item (top-level uitsluiting lsp/cache/__pycache__; geen diepe __pycache__-filter)." -ForegroundColor Yellow
        $srcNormFb = [System.IO.Path]::GetFullPath($Src.TrimEnd('\', '/'))
        $hermesNormFb = [System.IO.Path]::GetFullPath($hermesSource.TrimEnd('\', '/'))
        $skipNames = [System.Collections.Generic.HashSet[string]]::new([string[]]@('__pycache__'))
        if ($srcNormFb -eq $hermesNormFb) {
            [void]$skipNames.UnionWith([string[]]@('lsp', 'cache'))
        }
        Get-ChildItem -LiteralPath $Src -Force | ForEach-Object {
            if ($skipNames.Contains($_.Name)) { return }
            $target = Join-Path $Dst $_.Name
            Copy-Item -LiteralPath $_.FullName -Destination $target -Recurse -Force
        }
    }
}

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Hermes Agent: backup (institutioneel)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

if (-not (Test-Path $hermesSource)) {
    Write-Host "[ERROR] Bronmap $hermesSource niet gevonden!" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $backupRoot)) { New-Item -ItemType Directory -Path $backupRoot | Out-Null }
New-Item -ItemType Directory -Path $backupFolder | Out-Null

Write-Host "[1/11] Hermes-gebruikersmap ($hermesSource)..." -ForegroundColor Gray
Invoke-HermesRobocopyBackup -Src $hermesSource -Dst $backupFolder

$soulBackupPs1 = Join-Path $repoRoot 'windows/backup_soul_profiles.ps1'
$runtimePersonaFiles = @()
if (Test-Path -LiteralPath $soulBackupPs1) {
    Write-Host "[2/11] Runtime personas (LOCALAPPDATA\hermes SOUL)..." -ForegroundColor Gray
    $runtimePersonaFiles = @(& $soulBackupPs1 -BackupFolder $backupFolder)
} else {
    Write-Host "[2/11] [SKIP] backup_soul_profiles.ps1 ontbreekt" -ForegroundColor Yellow
}

Write-Host "[3/11] Repo windows\ -> repo_windows\ ..." -ForegroundColor Gray
$repoWindowsSrc = Join-Path $repoRoot "windows"
$repoWindowsDst = Join-Path $backupFolder "repo_windows"
if (Test-Path -LiteralPath $repoWindowsSrc) {
    Invoke-HermesRobocopyBackup -Src $repoWindowsSrc -Dst $repoWindowsDst
} else {
    Write-Host "  [SKIP] Geen map: $repoWindowsSrc" -ForegroundColor Yellow
}

Write-Host "[4/11] Repo assets\ -> repo_assets\ ..." -ForegroundColor Gray
$assetsSrc = Join-Path $repoRoot "assets"
$assetsDst = Join-Path $backupFolder "repo_assets"
if (Test-Path -LiteralPath $assetsSrc) {
    Invoke-HermesRobocopyBackup -Src $assetsSrc -Dst $assetsDst
} else {
    Write-Host "  [SKIP] Geen map: $assetsSrc" -ForegroundColor Yellow
}

Write-Host "[5/10] Kritieke repo-root -> repo_root\ (allowlist, veilig voor delen)..." -ForegroundColor Gray
$repoRootDst = Join-Path $backupFolder "repo_root"
New-Item -ItemType Directory -Path $repoRootDst -Force | Out-Null
# Alleen bestanden zonder typische secrets; géén cli-config.yaml / .env (kunnen keys bevatten).
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
# Release-notes (veel losse bestanden; geen secrets) — mee in repo_root voor delen/DR.
Get-ChildItem -LiteralPath $repoRoot -File -Filter 'RELEASE_v*.md' -ErrorAction SilentlyContinue |
    Sort-Object Name |
    ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $repoRootDst $_.Name) -Force
        $copiedRepoRoot += $_.Name
        Write-Host "  [OK] $($_.Name)" -ForegroundColor DarkGray
    }

Write-Host "[6/11] BACKUP_MANIFEST.json ..." -ForegroundColor Gray
$runtimeHome = Join-Path $env:LOCALAPPDATA 'hermes'
if (-not (Test-Path -LiteralPath (Join-Path $runtimeHome 'config.yaml'))) {
    $runtimeHome = $hermesSource
}
$manifest = [ordered]@{
    schema_version = 2
    format           = 'hermes_windows_backup'
    created_utc      = (Get-Date).ToUniversalTime().ToString('o')
    hostname         = $env:COMPUTERNAME
    windows_user     = $env:USERNAME
    repo_root        = $repoRoot
    hermes_profile   = $hermesSource
    hermes_runtime_home = $runtimeHome
    backup_folder    = $backupFolder
    repo_root_files  = $copiedRepoRoot
    includes         = @(
        'hermes_user_profile',
        'hermes_runtime_personas',
        'repo_windows',
        'repo_assets',
        'repo_root',
        'taskbar_shortcuts_in_backup_root',
        'BACKUP_MANIFEST'
    )
    runtime_personas = [ordered]@{
        backup_subdir = 'localappdata_hermes'
        files         = @($runtimePersonaFiles)
    }
}
$manifestPath = Join-Path $backupFolder 'BACKUP_MANIFEST.json'
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Host "  -> $manifestPath" -ForegroundColor DarkGray

Write-Host "[7/11] Taakbalk-.lnk in backup-map ..." -ForegroundColor Gray
$taskbarPs1 = Join-Path $repoRoot "windows\create_taskbar_shortcuts.ps1"
if (Test-Path -LiteralPath $taskbarPs1) {
    & $taskbarPs1 -RepoRoot $repoRoot -OutDir $backupFolder
} else {
    Write-Host "  [SKIP] create_taskbar_shortcuts.ps1 niet gevonden: $taskbarPs1" -ForegroundColor Yellow
}

Write-Host "[8/11] SQLite-integriteit (indien state.db) ..." -ForegroundColor Gray
$dbPath = Join-Path $backupFolder "state.db"
if (Test-Path $dbPath) {
    $verifyCmd = "import sqlite3; conn = sqlite3.connect(r'$dbPath'); res = conn.execute('PRAGMA integrity_check').fetchone(); print(res[0])"
    $res = $null
    $prevE = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $res = py -3 -c $verifyCmd 2>$null
    }
    if (-not $res) {
        $condaPy = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
        if (Test-Path -LiteralPath $condaPy) {
            $res = & $condaPy -c $verifyCmd 2>$null
        }
    }
    if (-not $res) {
        $res = python -c $verifyCmd 2>$null
    }
    $ErrorActionPreference = $prevE

    if ($res -eq "ok") {
        Write-Host "[SUCCESS] state.db: integrity_check ok." -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Database check: $res" -ForegroundColor Yellow
    }
} else {
    Write-Host "[INFO] Geen state.db in deze backup." -ForegroundColor Gray
}

Write-Host "[9/11] Taakbalk-.lnk in repo windows\ vernieuwen ..." -ForegroundColor Gray
$winDir = Join-Path $repoRoot "windows"
if (Test-Path -LiteralPath $taskbarPs1) {
    & $taskbarPs1 -RepoRoot $repoRoot -OutDir $winDir -Quiet
}

Write-Host "[10/11] Sync naar $env:USERPROFILE\.hermes\_local_assets ..." -ForegroundColor Gray

$syncScript = Join-Path $repoRoot "windows\sync_local_assets_to_backup.ps1"
if (Test-Path $syncScript) {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $syncScript
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
            Write-Host "[WARNING] sync_local_assets_to_backup.ps1 eindigde met code $LASTEXITCODE." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[WARNING] Sync naar _local_assets mislukt: $($_.Exception.Message)" -ForegroundColor Yellow
    } finally {
        $ErrorActionPreference = $prevEap
    }
} else {
    Write-Host "[WARNING] sync_local_assets_to_backup.ps1 niet gevonden: $syncScript" -ForegroundColor Yellow
}

Write-Host "[11/11] Verifieer Windows script-keten (bat -> ps1) ..." -ForegroundColor Gray
$verifyScript = Join-Path $repoRoot "windows\verify_windows_script_chain.ps1"
if (Test-Path -LiteralPath $verifyScript) {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $verifyScript -RepoRoot $repoRoot
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[WARNING] verify_windows_script_chain.ps1: keten incompleet (git pull / restore_local_assets)." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[WARNING] Verify mislukt: $($_.Exception.Message)" -ForegroundColor Yellow
    } finally {
        $ErrorActionPreference = $prevEap
    }
} else {
    Write-Host "[WARNING] verify_windows_script_chain.ps1 niet gevonden." -ForegroundColor Yellow
}

Write-Host "[OK] Backup voltooid: $backupFolder" -ForegroundColor Green

Write-Host ""
$nonInteractive = $SkipPause -or ($env:HERMES_BACKUP_NONINTERACTIVE -in @('1', 'true', 'True', 'yes', 'Yes'))
if (-not $nonInteractive) {
    pause
}
