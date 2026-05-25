# Gedeelde Hermes Windows backup/restore helpers (schema v3).
# Parity exclude-regels: hermes_cli/backup.py (_EXCLUDED_DIRS, WAL/SHM, pid-files).
# Dot-source: . (Join-HermesRepoPath -RepoRoot $PSScriptRoot -RelativePath 'scripts/HermesBackupCommon.ps1')

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'HermesHomeCommon.ps1')

function Get-HermesRobocopyExePath {
    $windir = if ($env:SystemRoot) { $env:SystemRoot } else { $env:WINDIR }
    foreach ($tail in @('System32\robocopy.exe', 'Sysnative\System32\robocopy.exe')) {
        $p = Join-Path $windir $tail
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $null
}

function Get-HermesBackupExcludeDirNames {
  # Directory name components skipped entirely (any depth) — mirror backup.py _EXCLUDED_DIRS + fork extras.
    return @(
        'hermes-agent',
        '__pycache__',
        '.git',
        'node_modules',
        'backups',
        'checkpoints',
        'lsp',
        'cache'
    )
}

function Get-HermesBackupExcludeFilePatterns {
    return @('*.log', '*.pyc', '*.pyo', '*.db-wal', '*.db-shm', '*.db-journal', 'gateway.pid', 'cron.pid')
}

function Get-HermesRobocopyExcludeDirsForSource {
    param(
        [Parameter(Mandatory)][string]$Src
    )
    $srcN = $Src.TrimEnd('\', '/')
    $xdDirs = [System.Collections.Generic.List[string]]::new()
    foreach ($name in (Get-HermesBackupExcludeDirNames)) {
        [void]$xdDirs.Add($name)
    }
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
    $dockerUnderSandboxesRoot = Join-Path $srcN 'docker'
    if (Test-Path -LiteralPath $dockerUnderSandboxesRoot) {
        Get-ChildItem -LiteralPath $dockerUnderSandboxesRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $homeCache = Join-Path $_.FullName 'home\.cache'
            if (Test-Path -LiteralPath $homeCache) {
                [void]$xdDirs.Add([System.IO.Path]::GetFullPath($homeCache))
            }
        }
    }
    return @($xdDirs | Select-Object -Unique)
}

function Invoke-HermesRobocopyMirror {
    param(
        [Parameter(Mandatory)][string]$Src,
        [Parameter(Mandatory)][string]$Dst,
        [string]$Label = ''
    )
    if (-not (Test-Path -LiteralPath $Src)) {
        Write-Host "  [SKIP] Bron ontbreekt: $Src" -ForegroundColor DarkYellow
        return $false
    }
    New-Item -ItemType Directory -Path $Dst -Force | Out-Null
    $robocopyExe = Get-HermesRobocopyExePath
  $srcN = $Src.TrimEnd('\', '/')
    if ($robocopyExe -and (Test-Path -LiteralPath $robocopyExe)) {
        $xdUnique = Get-HermesRobocopyExcludeDirsForSource -Src $srcN
        $xfPatterns = Get-HermesBackupExcludeFilePatterns
        $rcArgs = @(
            $srcN, $Dst, '/E', '/COPY:DT',
            '/R:1', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP'
        )
        if ($xfPatterns.Count -gt 0) {
            $rcArgs += '/XF'
            $rcArgs += $xfPatterns
        }
        if ($xdUnique.Count -gt 0) {
            $rcArgs += '/XD'
            $rcArgs += $xdUnique
        }
        & $robocopyExe @rcArgs
        $rc = $LASTEXITCODE
        if ($rc -ge 8) {
            throw "robocopy eindigde met foutcode $rc ($Src -> $Dst)"
        }
        $tag = if ($Label) { $Label } else { $Dst }
        Write-Host "  [OK] robocopy -> $tag" -ForegroundColor DarkGray
        return $true
    }
    Write-Host '  [WARN] Geen robocopy.exe — fallback Copy-Item (beperkte excludes).' -ForegroundColor Yellow
    $skipNames = [System.Collections.Generic.HashSet[string]]::new([string[]](Get-HermesBackupExcludeDirNames))
    Get-ChildItem -LiteralPath $Src -Force | ForEach-Object {
        if ($skipNames.Contains($_.Name)) { return }
        $target = Join-Path $Dst $_.Name
        Copy-Item -LiteralPath $_.FullName -Destination $target -Recurse -Force
    }
    return $true
}

function Test-HermesSafeForBackup {
    param(
        [string]$RuntimeRoot = ''
    )
    if (-not $RuntimeRoot) { $RuntimeRoot = Get-HermesRuntimeRoot }
    $reasons = [System.Collections.Generic.List[string]]::new()
    foreach ($pidName in @('gateway.pid', 'cron.pid')) {
        $pidPath = Join-Path $RuntimeRoot $pidName
        if (Test-Path -LiteralPath $pidPath) {
            [void]$reasons.Add("$pidName aanwezig onder $RuntimeRoot")
        }
    }
    foreach ($procName in @('hermes', 'hermes-gateway')) {
        $procs = @(Get-Process -Name $procName -ErrorAction SilentlyContinue)
        if ($procs.Count -gt 0) {
            $ids = ($procs | ForEach-Object { $_.Id }) -join ', '
            [void]$reasons.Add("proces $procName draait (PID: $ids)")
        }
    }
    if ($reasons.Count -eq 0) { return $true }
    Write-Host '[ERROR] Backup geblokkeerd — Hermes moet volledig gestopt zijn.' -ForegroundColor Red
    foreach ($r in $reasons) {
        Write-Host "  - $r" -ForegroundColor Yellow
    }
    Write-Host '  Sluit Hermes/gateway af en probeer opnieuw (MANAGE_BACKUPS.bat).' -ForegroundColor Yellow
    return $false
}

function Read-HermesBackupManifest {
    param([Parameter(Mandatory)][string]$BackupRoot)
    $manifestPath = Join-Path $BackupRoot 'BACKUP_MANIFEST.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) { return $null }
    try {
        return (Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Get-HermesBackupSchemaVersion {
    param([Parameter(Mandatory)][string]$BackupRoot)
    $manifest = Read-HermesBackupManifest -BackupRoot $BackupRoot
    if ($null -eq $manifest) {
        if (Test-Path -LiteralPath (Join-Path $BackupRoot 'runtime_hermes')) { return 3 }
        if (Test-Path -LiteralPath (Join-Path $BackupRoot 'localappdata_hermes')) { return 2 }
        return 1
    }
    $ver = $manifest.schema_version
    if ($null -ne $ver) { return [int]$ver }
    return 2
}

function Get-HermesPersonaBackupSubdir {
    param([Parameter(Mandatory)][string]$BackupRoot)
    $manifest = Read-HermesBackupManifest -BackupRoot $BackupRoot
    if ($null -ne $manifest -and $null -ne $manifest.runtime_personas) {
        $sub = $manifest.runtime_personas.backup_subdir
        if ($sub -and (Test-Path -LiteralPath (Join-Path $BackupRoot $sub))) {
            return [string]$sub
        }
    }
    foreach ($name in @('localappdata_hermes', 'localappdata_personas')) {
        if (Test-Path -LiteralPath (Join-Path $BackupRoot $name)) { return $name }
    }
    return $null
}

function Get-HermesInstitutionalDisplaySnapshot {
    param([Parameter(Mandatory)][string]$RuntimeRoot)
    $out = [ordered]@{}
    $profilesDir = Join-Path $RuntimeRoot 'profiles'
    if (-not (Test-Path -LiteralPath $profilesDir)) { return $out }
    Get-ChildItem -LiteralPath $profilesDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $cfgPath = Join-Path $_.FullName 'config.yaml'
        if (-not (Test-Path -LiteralPath $cfgPath)) { return }
        $snap = [ordered]@{}
        $lines = Get-Content -LiteralPath $cfgPath -ErrorAction SilentlyContinue
        $inDisplay = $false
        foreach ($line in $lines) {
            if ($line -match '^display\s*:\s*$') {
                $inDisplay = $true
                continue
            }
            if ($inDisplay) {
                if ($line -match '^\S' -and $line -notmatch '^display\s*:') {
                    $inDisplay = $false
                    continue
                }
                if ($line -match '^\s+(assistant_render_style|assistant_palette|streaming|final_response_markdown|compact)\s*:\s*(.+)\s*$') {
                    $snap[$Matches[1]] = $Matches[2].Trim().Trim('"').Trim("'")
                }
            }
        }
        if ($snap.Count -gt 0) {
            $out[$_.Name] = $snap
        }
    }
    return $out
}

function Test-HermesBackupPostVerify {
    param(
        [Parameter(Mandatory)][string]$BackupFolder,
        [switch]$Strict
    )
    $issues = [System.Collections.Generic.List[string]]::new()
    $runtimeDir = Join-Path $BackupFolder 'runtime_hermes'
    if (Test-Path -LiteralPath $runtimeDir) {
        $coreCfg = Join-Path $runtimeDir 'profiles\core\config.yaml'
        if (-not (Test-Path -LiteralPath $coreCfg)) {
            [void]$issues.Add('runtime_hermes/profiles/core/config.yaml ontbreekt')
        }
        $soulCount = @(Get-ChildItem -LiteralPath (Join-Path $runtimeDir 'profiles') -Recurse -Filter 'SOUL.md' -File -ErrorAction SilentlyContinue).Count
        if ($soulCount -lt 1) {
            [void]$issues.Add('geen SOUL.md onder runtime_hermes/profiles')
        }
    } elseif ($Strict) {
        [void]$issues.Add('runtime_hermes/ ontbreekt (schema v3)')
    }
    $personaDir = Get-HermesPersonaBackupSubdir -BackupRoot $BackupFolder
    if ($personaDir) {
        $personaCoreCfg = Join-Path $BackupFolder "$personaDir\profiles\core\config.yaml"
        if (-not (Test-Path -LiteralPath $personaCoreCfg)) {
            [void]$issues.Add("$personaDir/profiles/core/config.yaml ontbreekt")
        }
        $personaSoulCount = @(Get-ChildItem -LiteralPath (Join-Path $BackupFolder $personaDir) -Recurse -Filter 'SOUL.md' -File -ErrorAction SilentlyContinue).Count
        if ($personaSoulCount -lt 1) {
            [void]$issues.Add("$personaDir/ bevat geen SOUL.md")
        }
    } elseif ($Strict -and (Test-Path -LiteralPath $runtimeDir)) {
        [void]$issues.Add('localappdata_hermes/ ontbreekt terwijl runtime_hermes/ aanwezig is')
    }
    return @{
        Ok     = ($issues.Count -eq 0)
        Issues = @($issues)
    }
}

function Get-HermesPersonaRelativePaths {
    param([string]$ProfilesRoot = '')
    $paths = [System.Collections.Generic.List[string]]::new()
    [void]$paths.Add('config.yaml')
    [void]$paths.Add('SOUL.md')
    [void]$paths.Add('active_profile')
    [void]$paths.Add('institutional_new_chat_required.json')
    [void]$paths.Add('memories/USER.md')
    [void]$paths.Add('memories/MEMORY.md')
    [void]$paths.Add('profiles/core/KANBAN_WORKFLOWS.md')
    if ($ProfilesRoot -and (Test-Path -LiteralPath $ProfilesRoot)) {
        Get-ChildItem -LiteralPath $ProfilesRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $name = $_.Name
            [void]$paths.Add("profiles/$name/config.yaml")
            [void]$paths.Add("profiles/$name/SOUL.md")
            [void]$paths.Add("profiles/$name/memories/USER.md")
            [void]$paths.Add("profiles/$name/memories/MEMORY.md")
            if ($name -eq 'legal') {
                [void]$paths.Add('profiles/legal/LEGAL_ACTIVE_MATTERS.md')
            }
        }
    }
    return @($paths | Select-Object -Unique)
}

function Copy-HermesPersonaSubsetFromRuntime {
    param(
        [Parameter(Mandatory)][string]$RuntimeRoot,
        [Parameter(Mandatory)][string]$DstRoot
    )
    if (-not (Test-Path -LiteralPath (Join-Path $RuntimeRoot 'config.yaml'))) {
        return @()
    }
    New-Item -ItemType Directory -Path $DstRoot -Force | Out-Null
    $profilesDir = Join-Path $RuntimeRoot 'profiles'
    $relPaths = Get-HermesPersonaRelativePaths -ProfilesRoot $profilesDir
    $copied = [System.Collections.Generic.List[string]]::new()
    foreach ($rel in $relPaths) {
        $src = Join-HermesRepoPath -RepoRoot $RuntimeRoot -RelativePath $rel
        if (-not (Test-Path -LiteralPath $src)) { continue }
        $dst = Join-HermesRepoPath -RepoRoot $DstRoot -RelativePath $rel
        $parent = Split-Path -Parent $dst
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Copy-Item -LiteralPath $src -Destination $dst -Force
        [void]$copied.Add(($rel -replace '\\', '/'))
    }
    return $copied.ToArray()
}

function Invoke-HermesRestorePersonaSubsetFromRuntimeBackup {
    param(
        [Parameter(Mandatory)][string]$RuntimeBackupRoot,
        [Parameter(Mandatory)][string]$RuntimeDst
    )
    $profilesRoot = Join-Path $RuntimeBackupRoot 'profiles'
    $relPaths = Get-HermesPersonaRelativePaths -ProfilesRoot $profilesRoot
    $count = 0
    foreach ($rel in $relPaths) {
        $src = Join-HermesRepoPath -RepoRoot $RuntimeBackupRoot -RelativePath $rel
        if (-not (Test-Path -LiteralPath $src)) { continue }
        $target = Join-HermesRepoPath -RepoRoot $RuntimeDst -RelativePath $rel
        $parent = Split-Path -Parent $target
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Copy-Item -LiteralPath $src -Destination $target -Force
        Write-Host "  [OK] $rel" -ForegroundColor Green
        $count++
    }
    return $count
}

function Assert-BackupManifestCompatible {
    param(
        [Parameter(Mandatory)][string]$BackupRoot,
        [int[]]$AllowedVersions = @(1, 2, 3)
    )
    $ver = Get-HermesBackupSchemaVersion -BackupRoot $BackupRoot
    if ($ver -notin $AllowedVersions) {
        throw "Backup schema v$ver niet ondersteund (verwacht: $($AllowedVersions -join ', '))"
    }
    return $ver
}
function Invoke-HermesRestorePersonaFiles {
    param(
        [Parameter(Mandatory)][string]$PersonaSrc,
        [Parameter(Mandatory)][string]$RuntimeDst
    )
    if (-not (Test-Path -LiteralPath $PersonaSrc)) { return 0 }
    $count = 0
    Get-ChildItem -LiteralPath $PersonaSrc -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($PersonaSrc.Length).TrimStart('\', '/')
        $target = Join-Path $RuntimeDst $rel
        $parent = Split-Path -Parent $target
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Copy-Item -LiteralPath $_.FullName -Destination $target -Force
        Write-Host "  [OK] $rel" -ForegroundColor Green
        $count++
    }
    return $count
}
