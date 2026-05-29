#requires -Version 5.1
# Persistente Hermes-snelkoppelingen (%LOCALAPPDATA%\Hermes) + taakbalk/bureaublad-reparatie na update.
# Dot-source vanuit fix_hermes_taskbar_pins.ps1; niet handmatig starten.

function Get-HermesPersistentShortcutsDir {
    $local = Get-HermesRealLocalAppData
    if (-not $local) { return $null }
    return (Join-Path $local (Join-Path 'Hermes' 'shortcuts'))
}

function Get-HermesTaskbarPinnedDir {
    return (Join-Path $env:APPDATA (Join-Path 'Microsoft' (Join-Path 'Internet Explorer' (Join-Path 'Quick Launch' (Join-Path 'User Pinned' 'TaskBar')))))
}

function Write-HermesInstallState {
    param([Parameter(Mandatory)][string]$RepoRoot)
    $local = Get-HermesRealLocalAppData
    if (-not $local) { return }
    $dir = Join-Path $local 'Hermes'
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    @{
        repoRoot  = (Resolve-Path -LiteralPath $RepoRoot).Path
        updatedAt = (Get-Date).ToUniversalTime().ToString('o')
    } | ConvertTo-Json -Compress | Set-Content -LiteralPath (Join-Path $dir 'install-state.json') -Encoding UTF8
}

function Get-HermesShortcutCatalog {
  <#
    .SYNOPSIS
        Canonieke Hermes-snelkoppelingen (één bron voor windows\, AppData en taakbalk-pins).
  #>
    param([Parameter(Mandatory)][string]$RepoRoot)

    . (Join-Path (Split-Path -Parent $PSScriptRoot) 'launcher_config.ps1')
    $startFull = Get-HermesStartLauncherRelativePath -RepoRoot $RepoRoot -LaunchProfile full
    $startMin = Get-HermesStartLauncherRelativePath -RepoRoot $RepoRoot -LaunchProfile minimal

    return @(
        @{
            Role        = 'Start'
            FileName    = 'Start Hermes - naar taakbalk slepen.lnk'
            BatRelative = $startFull
            KeepOpen    = $false
            UseStartShortcut = $true
            LaunchProfile = 'full'
        },
        @{
            Role        = 'StartFast'
            FileName    = 'Start Hermes (snel) - naar taakbalk slepen.lnk'
            BatRelative = $startMin
            KeepOpen    = $false
            UseStartShortcut = $true
            LaunchProfile = 'minimal'
        },
        @{
            Role        = 'Setup'
            FileName    = 'Hermes - setup Windows - naar taakbalk slepen.lnk'
            BatRelative = 'windows/SETUP_HERMES.bat'
            KeepOpen    = $false
        },
        @{
            Role        = 'Backup'
            FileName    = 'Hermes - backup - naar taakbalk slepen.lnk'
            BatRelative = 'windows/MANAGE_BACKUPS.bat'
            KeepOpen    = $false
        },
        @{
            Role        = 'Restore'
            FileName    = 'Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk'
            BatRelative = 'windows/restore_local_assets.bat'
            KeepOpen    = $false
        },
        @{
            Role        = 'Update'
            FileName    = 'Hermes - update - naar taakbalk slepen.lnk'
            BatRelative = 'windows/UPDATE_HERMES.bat'
            KeepOpen    = $false
        },
        @{
            Role        = 'Rag'
            FileName    = 'Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk'
            BatRelative = 'windows/RAG_KNOWLEDGE_UPDATE.bat'
            KeepOpen    = $true
        },
        @{
            Role        = 'Obsidian'
            FileName    = 'Hermes - Obsidian vault - naar taakbalk slepen.lnk'
            BatRelative = 'windows/OPEN_OBSIDIAN_VAULT.bat'
            KeepOpen    = $false
        },
        @{
            Role        = 'OpenSetup'
            FileName    = 'Hermes - Open Setup - naar taakbalk slepen.lnk'
            BatRelative = 'windows/OPEN_SETUP.bat'
            KeepOpen    = $false
        }
    )
}

function Get-HermesShortcutRoleFromBatPath {
    param(
        [string]$BatPath,
        [Parameter(Mandatory)][string]$RepoRoot
    )
    $fixed = Repair-HermesBatPathForRepo -BatPath $BatPath -RepoRoot $RepoRoot
    if (-not $fixed) { return $null }
    $leaf = (Split-Path -Leaf $fixed).ToLowerInvariant()
    $map = @{
        'start_hermes_full.bat'      = 'Start'
        'start_hermes.bat'           = 'Start'
        'start_hermes_split.bat'     = 'Start'
        'start_hermes_minimal.bat'   = 'StartFast'
        'setup_hermes.bat'           = 'Setup'
        'manage_backups.bat'         = 'Backup'
        'restore_local_assets.bat'   = 'Restore'
        'update_hermes.bat'          = 'Update'
        'rag_knowledge_update.bat'   = 'Rag'
        'open_obsidian_vault.bat'    = 'Obsidian'
        'open_setup.bat'             = 'OpenSetup'
        'hermes_met_logo.bat'        = 'Start'
    }
    if ($map.ContainsKey($leaf)) { return $map[$leaf] }
    return $null
}

function Get-HermesShortcutRoleFromPinName {
    param([string]$PinLeaf)
    $n = $PinLeaf.ToLowerInvariant()
    if ($n -match 'start hermes \(snel\)|snel\)') { return 'StartFast' }
    if ($n -match 'start hermes|hermes agent') { return 'Start' }
    if ($n -match 'update') { return 'Update' }
    if ($n -match 'open setup') { return 'OpenSetup' }
    if ($n -match 'setup') { return 'Setup' }
    if ($n -match 'backup') { return 'Backup' }
    if ($n -match 'herstellen|restore') { return 'Restore' }
    if ($n -match 'rag|kennis') { return 'Rag' }
    if ($n -match 'obsidian|vault') { return 'Obsidian' }
    return $null
}

function Get-HermesShortcutRoleFromShortcut {
    param(
        [Parameter(Mandatory)][string]$ShortcutPath,
        [Parameter(Mandatory)][string]$RepoRoot
    )
    $leaf = Split-Path $ShortcutPath -Leaf
    $byName = Get-HermesShortcutRoleFromPinName -PinLeaf $leaf
    if ($byName) { return $byName }

    $bat = Get-HermesShortcutResolvedBatPath -ShortcutPath $ShortcutPath -RepoRoot $RepoRoot
    if ($bat) {
        $byBat = Get-HermesShortcutRoleFromBatPath -BatPath $bat -RepoRoot $RepoRoot
        if ($byBat) { return $byBat }
    }
    return $null
}

function New-HermesCatalogShortcut {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][hashtable]$Entry,
        [Parameter(Mandatory)][string]$ShortcutPath,
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$WindowsDir
    )
    if (-not $PSCmdlet.ShouldProcess($ShortcutPath, 'Create Hermes shortcut')) { return $false }
    $batPath = Join-Path $RepoRoot ($Entry.BatRelative -replace '/', '\')
    if (-not (Test-Path -LiteralPath $batPath)) { return $false }
    $iconPath = Get-HermesTaskbarRoleIconPath -Role $Entry.Role -WindowsDir $WindowsDir
    if (-not $iconPath) { return $false }

    if ($Entry.UseStartShortcut) {
        return (Set-HermesStartShellShortcut -ShortcutPath $ShortcutPath -RepoRoot $RepoRoot `
                -IconIcoPath $iconPath -LaunchProfile $Entry.LaunchProfile)
    }
    return (Set-HermesShellShortcut -ShortcutPath $ShortcutPath -TargetBatPath $batPath `
            -IconIcoPath $iconPath -WorkingDirectory $RepoRoot `
            -KeepCmdWindowOpen:([bool]$Entry.KeepOpen))
}

function Sync-HermesCatalogShortcuts {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$WindowsDir,
        [string[]]$TargetDirs,
        [switch]$Quiet
    )
    $catalog = Get-HermesShortcutCatalog -RepoRoot $RepoRoot
    $ok = 0
    foreach ($dir in $TargetDirs) {
        if (-not $dir) { continue }
        if (-not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
        foreach ($entry in $catalog) {
            $lnk = Join-Path $dir $entry.FileName
            if (New-HermesCatalogShortcut -Entry $entry -ShortcutPath $lnk -RepoRoot $RepoRoot -WindowsDir $WindowsDir) {
                $ok++
            } elseif (-not $Quiet) {
                Write-Host ('  [SKIP] ' + $entry.FileName + ' — bat ontbreekt') -ForegroundColor Yellow
            }
        }
    }
    return $ok
}

function Repair-HermesShellShortcutInPlace {
    param(
        [Parameter(Mandatory)][string]$ShortcutPath,
        [Parameter(Mandatory)][string]$Role,
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$WindowsDir
    )
    $catalog = Get-HermesShortcutCatalog -RepoRoot $RepoRoot
    $entry = $catalog | Where-Object { $_.Role -eq $Role } | Select-Object -First 1
    if (-not $entry) { return $false }
    return (New-HermesCatalogShortcut -Entry $entry -ShortcutPath $ShortcutPath -RepoRoot $RepoRoot -WindowsDir $WindowsDir)
}

function Repair-HermesPinnedAndDesktopShortcuts {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$WindowsDir,
        [switch]$Quiet
    )
    $repaired = 0
    $dirs = @()
    $pinDir = Get-HermesTaskbarPinnedDir
    if ($pinDir -and (Test-Path -LiteralPath $pinDir)) { $dirs += $pinDir }
    $desk = [Environment]::GetFolderPath('Desktop')
    if ($desk) { $dirs += $desk }

    foreach ($dir in $dirs) {
        Get-ChildItem -LiteralPath $dir -Filter 'Hermes*.lnk' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -notmatch ' \(\d+\)\.lnk$' } |
            ForEach-Object {
                $health = Test-HermesShortcutPathHealth -ShortcutPath $_.FullName -RepoRoot $RepoRoot
                $role = Get-HermesShortcutRoleFromShortcut -ShortcutPath $_.FullName -RepoRoot $RepoRoot
                if (-not $role) { return }
                if ($health.Ok -and (Test-HermesShortcutIconPathValid -IconPath ((New-Object -ComObject WScript.Shell).CreateShortcut($_.FullName).IconLocation))) {
                    return
                }
                if (Repair-HermesShellShortcutInPlace -ShortcutPath $_.FullName -Role $role -RepoRoot $RepoRoot -WindowsDir $WindowsDir) {
                    $script:repaired++
                    if (-not $Quiet) {
                        Write-Host ('  [OK] Hersteld: ' + $_.Name) -ForegroundColor Green
                    }
                }
            }
    }
    return $repaired
}

function Invoke-HermesShortcutSyncRepair {
    <#
    .SYNOPSIS
        Volledige sync: iconen, persistente + windows\.lnk, alle Hermes taakbalk/bureaublad-pins.
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$WindowsDir = '',
        [switch]$Quiet,
        [switch]$SkipIconGen
    )
    $repo = (Resolve-Path -LiteralPath $RepoRoot).Path
    if (-not $WindowsDir) {
        $WindowsDir = Join-Path $repo 'windows'
    } else {
        $WindowsDir = (Resolve-Path -LiteralPath $WindowsDir).Path
    }

    Write-HermesInstallState -RepoRoot $repo

    if (-not $SkipIconGen) {
        $icoGenPy = Join-Path $WindowsDir (Join-Path 'tools' 'generate_colored_hermes_icons.py')
        if (Test-Path -LiteralPath $icoGenPy) {
            $needIconGen = Test-HermesWindowsIconRegenNeeded -RepoRoot $repo -WindowsDir $WindowsDir
            if ($needIconGen) {
                if (-not $Quiet) {
                    Write-Host '[INFO] Icoonset vernieuwen (PNG/ICO desync of ontbrekend)...' -ForegroundColor Gray
                }
                [void](Invoke-HermesColoredIconsFromPng -IconGeneratorPy $icoGenPy -Quiet:$Quiet)
            } elseif (-not $Quiet) {
                Write-Host '[INFO] Icoonset actueel — generator overgeslagen.' -ForegroundColor DarkGray
            }
        }
    }
    [void](Publish-HermesShortcutIconCache -WindowsDir $WindowsDir)

    $persistDir = Get-HermesPersistentShortcutsDir
    $targets = @($WindowsDir)
    if ($persistDir) { $targets += $persistDir }

    if (-not $Quiet) {
        Write-Host '[INFO] Snelkoppelingen synchroniseren (windows + AppData)...' -ForegroundColor Gray
    }
    [void](Sync-HermesCatalogShortcuts -RepoRoot $repo -WindowsDir $WindowsDir -TargetDirs $targets -Quiet:$Quiet)

    $pinnedDir = Get-HermesTaskbarPinnedDir
    if ($pinnedDir -and (Test-Path -LiteralPath $pinnedDir)) {
        Get-ChildItem -LiteralPath $pinnedDir -Filter 'Hermes*.lnk' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match ' \(\d+\)\.lnk$' } |
            ForEach-Object {
                if ($PSCmdlet.ShouldProcess($_.FullName, 'Remove', 'Duplicate Hermes pin')) {
                    Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
                }
            }
    }

    $catalog = Get-HermesShortcutCatalog -RepoRoot $repo
    if ($pinnedDir -and (Test-Path -LiteralPath $pinnedDir)) {
        foreach ($entry in $catalog) {
            if ($entry.Role -eq 'OpenSetup') { continue }
            $dest = Join-Path $pinnedDir $entry.FileName
            if (-not (New-HermesCatalogShortcut -Entry $entry -ShortcutPath $dest -RepoRoot $repo -WindowsDir $WindowsDir)) {
                continue
            }
            if (-not $Quiet) {
                Write-Host ('  [OK] Taakbalk-pin: ' + $entry.FileName) -ForegroundColor Green
            }
        }
    }

    $extra = Repair-HermesPinnedAndDesktopShortcuts -RepoRoot $repo -WindowsDir $WindowsDir -Quiet:$Quiet
    if (-not $Quiet -and $extra -gt 0) {
        Write-Host ("  [OK] Extra pins/bureaublad hersteld: $extra") -ForegroundColor Green
    }

    if (Get-Command Clear-HermesShellIconCache -ErrorAction SilentlyContinue) {
        Clear-HermesShellIconCache
    }
    return 0
}
