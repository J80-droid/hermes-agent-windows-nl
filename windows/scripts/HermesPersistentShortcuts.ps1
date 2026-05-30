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

function Test-HermesManagedPinLeaf {
    param([Parameter(Mandatory)][string]$Leaf)
    $n = $Leaf.ToLowerInvariant()
    return ($n -match 'hermes|start hermes')
}

function Test-HermesShortcutReferencesHermesProduct {
    param(
        [Parameter(Mandatory)][string]$ShortcutPath,
        [string]$RepoRoot = ''
    )
    if (Test-HermesManagedPinLeaf -Leaf (Split-Path -Leaf $ShortcutPath)) { return $true }
    if (-not (Test-Path -LiteralPath $ShortcutPath)) { return $false }
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($ShortcutPath)
    $blob = @($s.TargetPath, $s.Arguments, $s.WorkingDirectory, $s.Description) -join ' '
    if ($blob -match 'hermes|hudui|hermesos|hermes-agent|hermes_agent') { return $true }
    if ($RepoRoot -and $blob -match [regex]::Escape($RepoRoot)) { return $true }
    return $false
}

function Get-HermesTaskbarPinShortcutCandidates {
    param(
        [Parameter(Mandatory)][string]$PinnedDir,
        [string]$RepoRoot = ''
    )
    if (-not (Test-Path -LiteralPath $PinnedDir)) { return @() }
    return @(Get-ChildItem -LiteralPath $PinnedDir -Filter '*.lnk' -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -notmatch ' \(\d+\)\.lnk$' -and
            (Test-HermesShortcutReferencesHermesProduct -ShortcutPath $_.FullName -RepoRoot $RepoRoot)
        })
}

function Test-HermesShortcutLaunchTargetsExist {
    param(
        [Parameter(Mandatory)][string]$ShortcutPath,
        [Parameter(Mandatory)][string]$RepoRoot
    )
    if (-not (Test-Path -LiteralPath $ShortcutPath)) { return $false }
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($ShortcutPath)
    if ($s.TargetPath) {
        if ($s.TargetPath -match '\.lnk$') {
            if (-not (Test-Path -LiteralPath $s.TargetPath)) { return $false }
        } elseif ($s.TargetPath -match '\.(exe|bat|cmd)$') {
            if (-not (Test-Path -LiteralPath $s.TargetPath)) {
                $repaired = Repair-HermesBatPathForRepo -BatPath $s.TargetPath -RepoRoot $RepoRoot
                if (-not $repaired) { return $false }
            }
        } elseif (-not (Test-Path -LiteralPath $s.TargetPath)) {
            return $false
        }
    }
    $bat = Get-HermesShortcutResolvedBatPath -ShortcutPath $ShortcutPath -RepoRoot $RepoRoot
    if ($bat -and -not (Test-Path -LiteralPath $bat)) { return $false }
    return $true
}

function Remove-HermesRedundantLegacyStartPins {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$PinnedDir,
        [switch]$Quiet
    )
    $canonical = 'Start Hermes - naar taakbalk slepen.lnk'
    $legacy = @(
        'Start Hermes (volledig) - naar taakbalk slepen.lnk',
        'Hermes Agent - naar taakbalk slepen.lnk'
    )
    $canonPath = Join-Path $PinnedDir $canonical
    if (-not (Test-Path -LiteralPath $canonPath)) { return 0 }
    $removed = 0
    foreach ($leaf in $legacy) {
        $p = Join-Path $PinnedDir $leaf
        if (-not (Test-Path -LiteralPath $p)) { continue }
        if ($PSCmdlet.ShouldProcess($p, 'Remove', 'Redundant legacy Hermes start pin')) {
            Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
            $script:removed++
            if (-not $Quiet) {
                Write-Host ('  [OK] Dubbele start-pin verwijderd: ' + $leaf) -ForegroundColor Yellow
            }
        }
    }
    return $removed
}

function Remove-HermesUnlaunchableTaskbarPins {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$PinnedDir,
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$WindowsDir,
        [switch]$Quiet
    )
    $removed = 0
    foreach ($item in (Get-HermesTaskbarPinShortcutCandidates -PinnedDir $PinnedDir -RepoRoot $RepoRoot)) {
        if (Test-HermesShortcutLaunchTargetsExist -ShortcutPath $item.FullName -RepoRoot $RepoRoot) {
            continue
        }
        $role = Get-HermesShortcutRoleFromShortcut -ShortcutPath $item.FullName -RepoRoot $RepoRoot
        if ($role) {
            if (Repair-HermesShellShortcutInPlace -ShortcutPath $item.FullName -Role $role -RepoRoot $RepoRoot -WindowsDir $WindowsDir) {
                if (Test-HermesShortcutLaunchTargetsExist -ShortcutPath $item.FullName -RepoRoot $RepoRoot) {
                    continue
                }
            }
        }
        if ($PSCmdlet.ShouldProcess($item.FullName, 'Remove', 'Unlaunchable Hermes taskbar pin')) {
            Remove-Item -LiteralPath $item.FullName -Force -ErrorAction SilentlyContinue
            $script:removed++
            if (-not $Quiet) {
                Write-Host ('  [OK] Kapotte pin verwijderd (voorkomt pop-up): ' + $item.Name) -ForegroundColor Yellow
            }
        }
    }
    return $removed
}

function Write-HermesOrphanExePinAdvisory {
    param([switch]$Quiet)
    $knownDead = @(
        'D:\A.I\APPS\Hermes_agent\hermes-hudui\src-tauri\target\debug\hermes-hudui.exe'
    )
    $found = @($knownDead | Where-Object { -not (Test-Path -LiteralPath $_) })
    if ($found.Count -eq 0) { return }
    if (-not $Quiet) {
        Write-Host '[WARN] Oude Hermes-app-pins (geen .lnk in User Pinned\TaskBar):' -ForegroundColor Yellow
        foreach ($p in $found) {
            Write-Host ('       ' + $p) -ForegroundColor DarkYellow
        }
        Write-Host '       Los van taakbalk + klik Ja bij pop-up, of pin opnieuw via windows\Start Hermes - naar taakbalk slepen.lnk' -ForegroundColor Gray
    }
}

function Get-HermesManagedPinShortcuts {
    param([Parameter(Mandatory)][string]$Dir)
    if (-not (Test-Path -LiteralPath $Dir)) { return @() }
    return @(Get-ChildItem -LiteralPath $Dir -Filter '*.lnk' -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -notmatch ' \(\d+\)\.lnk$' -and (Test-HermesManagedPinLeaf -Leaf $_.Name)
        })
}

function Remove-HermesDuplicateTaskbarPins {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$PinnedDir,
        [switch]$Quiet
    )
    if (-not (Test-Path -LiteralPath $PinnedDir)) { return 0 }
    $removed = 0
    Get-ChildItem -LiteralPath $PinnedDir -Filter '*.lnk' -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match ' \(\d+\)\.lnk$' -and
            (Test-HermesManagedPinLeaf -Leaf ($_.Name -replace ' \(\d+\)\.lnk$', '.lnk'))
        } |
        ForEach-Object {
            if ($PSCmdlet.ShouldProcess($_.FullName, 'Remove', 'Duplicate Hermes taskbar pin')) {
                Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
                $script:removed++
            }
        }
    if (-not $Quiet -and $removed -gt 0) {
        Write-Host ("  [OK] Dubbele taakbalk-pins verwijderd: $removed") -ForegroundColor Green
    }
    return $removed
}

function Remove-HermesBrokenManagedPinsWithoutRole {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$Dir,
        [Parameter(Mandatory)][string]$RepoRoot,
        [switch]$Quiet
    )
    $removed = 0
    foreach ($item in (Get-HermesManagedPinShortcuts -Dir $Dir)) {
        $role = Get-HermesShortcutRoleFromShortcut -ShortcutPath $item.FullName -RepoRoot $RepoRoot
        if ($role) { continue }
        $health = Test-HermesShortcutPathHealth -ShortcutPath $item.FullName -RepoRoot $RepoRoot
        if ($health.Ok) { continue }
        if ($PSCmdlet.ShouldProcess($item.FullName, 'Remove', 'Broken Hermes pin without role')) {
            Remove-Item -LiteralPath $item.FullName -Force -ErrorAction SilentlyContinue
            $script:removed++
            if (-not $Quiet) {
                Write-Host ('  [OK] Verouderde pin verwijderd: ' + $item.Name) -ForegroundColor Yellow
            }
        }
    }
    return $removed
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
        [switch]$Quiet,
        [switch]$RefreshAllTaskbarPins
    )
    $repaired = 0
    $pinDir = Get-HermesTaskbarPinnedDir
    $desk = [Environment]::GetFolderPath('Desktop')
    $targets = @()
    if ($pinDir -and (Test-Path -LiteralPath $pinDir)) {
        $targets += @{ Dir = $pinDir; IsTaskbar = $true }
    }
    if ($desk) {
        $targets += @{ Dir = $desk; IsTaskbar = $false }
    }

    foreach ($target in $targets) {
        $items = if ($target.IsTaskbar) {
            Get-HermesTaskbarPinShortcutCandidates -PinnedDir $target.Dir -RepoRoot $RepoRoot
        } else {
            Get-HermesManagedPinShortcuts -Dir $target.Dir
        }
        foreach ($item in $items) {
            $role = Get-HermesShortcutRoleFromShortcut -ShortcutPath $item.FullName -RepoRoot $RepoRoot
            if (-not $role) { continue }

            $health = Test-HermesShortcutPathHealth -ShortcutPath $item.FullName -RepoRoot $RepoRoot
            $iconOk = $true
            if ($health.Ok) {
                $iconLoc = (New-Object -ComObject WScript.Shell).CreateShortcut($item.FullName).IconLocation
                $iconOk = Test-HermesShortcutIconPathValid -IconPath $iconLoc
            }
            $needsRepair = (-not $health.Ok) -or (-not $iconOk)
            if ($target.IsTaskbar -and ($RefreshAllTaskbarPins -or $needsRepair)) {
                $needsRepair = $true
            }
            if (-not $needsRepair) { continue }

            if (Repair-HermesShellShortcutInPlace -ShortcutPath $item.FullName -Role $role -RepoRoot $RepoRoot -WindowsDir $WindowsDir) {
                $script:repaired++
                if (-not $Quiet) {
                    Write-Host ('  [OK] Hersteld: ' + $item.Name) -ForegroundColor Green
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
        Write-HermesOrphanExePinAdvisory -Quiet:$Quiet
        [void](Remove-HermesDuplicateTaskbarPins -PinnedDir $pinnedDir -Quiet:$Quiet)
        [void](Repair-HermesPinnedAndDesktopShortcuts -RepoRoot $repo -WindowsDir $WindowsDir `
            -Quiet:$Quiet -RefreshAllTaskbarPins)
    }

    $catalog = Get-HermesShortcutCatalog -RepoRoot $repo
    if ($pinnedDir -and (Test-Path -LiteralPath $pinnedDir)) {
        foreach ($entry in $catalog) {
            $dest = Join-Path $pinnedDir $entry.FileName
            if (-not (New-HermesCatalogShortcut -Entry $entry -ShortcutPath $dest -RepoRoot $repo -WindowsDir $WindowsDir)) {
                continue
            }
            if (-not $Quiet) {
                Write-Host ('  [OK] Taakbalk-pin: ' + $entry.FileName) -ForegroundColor Green
            }
        }
    }

    if ($pinnedDir -and (Test-Path -LiteralPath $pinnedDir)) {
        [void](Remove-HermesBrokenManagedPinsWithoutRole -Dir $pinnedDir -RepoRoot $repo -Quiet:$Quiet)
        [void](Remove-HermesRedundantLegacyStartPins -PinnedDir $pinnedDir -Quiet:$Quiet)
        [void](Remove-HermesUnlaunchableTaskbarPins -PinnedDir $pinnedDir -RepoRoot $repo -WindowsDir $WindowsDir -Quiet:$Quiet)
    }

    $extra = Repair-HermesPinnedAndDesktopShortcuts -RepoRoot $repo -WindowsDir $WindowsDir `
        -Quiet:$Quiet -RefreshAllTaskbarPins
    if (-not $Quiet -and $extra -gt 0) {
        Write-Host ("  [OK] Taakbalk/bureaublad-pins bijgewerkt: $extra") -ForegroundColor Green
    }

    if (Get-Command Clear-HermesShellIconCache -ErrorAction SilentlyContinue) {
        Clear-HermesShellIconCache
    }
    return 0
}
