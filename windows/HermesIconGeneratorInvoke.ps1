# Gedeeld door sync_local_assets_to_backup.ps1 en create_taskbar_shortcuts.ps1
# Draait generate_colored_hermes_icons.py zodat hermes_logo.ico gelijk loopt met de PNG-gebaseerde varianten.

function Publish-HermesShortcutIconCache {
    <#
    .SYNOPSIS
        Kopieert hermes*.ico naar %LOCALAPPDATA%\Hermes\shortcut-icons (stabiel pad voor Shell).
    #>
    param([Parameter(Mandatory)][string]$WindowsDir)
    $cacheDir = Join-Path $env:LOCALAPPDATA (Join-Path 'Hermes' 'shortcut-icons')
    New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
    Get-ChildItem -LiteralPath $WindowsDir -Filter 'hermes*.ico' -File -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $cacheDir $_.Name) -Force
    }
    return $cacheDir
}

function Get-HermesShellShortcutIconLocation {
    param([Parameter(Mandatory)][string]$IcoPath)
    if (-not (Test-Path -LiteralPath $IcoPath)) { return $null }
    # Zelfde map als .lnk (windows\) — betrouwbaarder dan alleen AppData-cache voor Verkenner.
    $resolved = (Resolve-Path -LiteralPath $IcoPath).Path
    $cacheDir = Join-Path $env:LOCALAPPDATA (Join-Path 'Hermes' 'shortcut-icons')
    $cached = Join-Path $cacheDir (Split-Path -Leaf $IcoPath)
    if (Test-Path -LiteralPath $cached) {
        $resolved = (Resolve-Path -LiteralPath $cached).Path
    }
    return ($resolved + ',0')
}

function Get-HermesCmdShortcutArgumentLine {
    <#
    .SYNOPSIS
        cmd.exe Arguments voor .lnk: alleen /c call + bat (werkmap via .lnk WorkingDirectory).
        Geen geneste cd-quotes — die breken onder Windows Terminal als standaard host.
    #>
    param(
        [Parameter(Mandatory)][string]$BatchPath,
        [switch]$KeepWindowOpen,
        [string]$WorkingDirectory = ''
    )
    $null = $WorkingDirectory
    $cmdFlag = if ($KeepWindowOpen) { '/k' } else { '/c' }
    return ('{0} call ""{1}""' -f $cmdFlag, $BatchPath)
}

function Get-HermesWtShortcutArgumentLine {
    <#
    .SYNOPSIS
        wt.exe Arguments: zelfde patroon als Start-snelkoppeling (-M -d repo cmd /c call bat).
    #>
    param(
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [Parameter(Mandatory)][string]$BatchPath,
        [switch]$KeepWindowOpen
    )
    $cmdExe = Join-Path $env:SystemRoot 'System32\cmd.exe'
    $cmdFlag = if ($KeepWindowOpen) { '/k' } else { '/c' }
    return ('-M -d "{0}" {1} {2} call "{3}"' -f $WorkingDirectory, $cmdExe, $cmdFlag, $BatchPath)
}

function Get-HermesBatPathFromShortcutArguments {
    param([string]$Arguments)
    if ([string]::IsNullOrWhiteSpace($Arguments)) { return $null }
    $patterns = @(
        'call\s+""([^""]+\.(?:bat|cmd))""',
        'call\s+"([^"]+\.(?:bat|cmd))"',
        '/k\s+call\s+""([^""]+\.(?:bat|cmd))""',
        '/k\s+call\s+"([^"]+\.(?:bat|cmd))"'
    )
    foreach ($pat in $patterns) {
        if ($Arguments -match $pat) {
            return $Matches[1]
        }
    }
    return $null
}

function Get-HermesShortcutResolvedBatPath {
    <#
    .SYNOPSIS
        Bepaalt het .bat/.cmd-doel van een Hermes-.lnk (cmd /c, wt.exe of directe .bat-target).
    #>
    param(
        [Parameter(Mandatory)][string]$ShortcutPath
    )
    if (-not (Test-Path -LiteralPath $ShortcutPath)) { return $null }
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($ShortcutPath)
    $target = $s.TargetPath
    if ($target -match '\.(bat|cmd)$' -and (Test-Path -LiteralPath $target)) {
        return (Resolve-Path -LiteralPath $target).Path
    }
    $fromArgs = Get-HermesBatPathFromShortcutArguments -Arguments $s.Arguments
    if ($fromArgs -and (Test-Path -LiteralPath $fromArgs)) {
        return (Resolve-Path -LiteralPath $fromArgs).Path
    }
    return $null
}

function Test-HermesShortcutPathHealth {
    <#
    .SYNOPSIS
        Valideert .lnk: bat bestaat, werkmap = repo-root, volledig pad in call (geen relatieve stub).
    #>
    param(
        [Parameter(Mandatory)][string]$ShortcutPath,
        [Parameter(Mandatory)][string]$RepoRoot
    )
    $issues = [System.Collections.Generic.List[string]]::new()
    if (-not (Test-Path -LiteralPath $ShortcutPath)) {
        $issues.Add('Snelkoppeling ontbreekt')
        return @{ Ok = $false; BatPath = $null; Issues = $issues }
    }
    $repoResolved = (Resolve-Path -LiteralPath $RepoRoot).Path
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($ShortcutPath)
    $batPath = Get-HermesShortcutResolvedBatPath -ShortcutPath $ShortcutPath
    if (-not $batPath) {
        $issues.Add('Geen .bat/.cmd-doel gevonden in Target of Arguments')
    } elseif (-not (Test-Path -LiteralPath $batPath)) {
        $issues.Add("Bat ontbreekt: $batPath")
    }
    if ($s.WorkingDirectory) {
        if (-not (Test-Path -LiteralPath $s.WorkingDirectory)) {
            $issues.Add("Werkmap ontbreekt: $($s.WorkingDirectory)")
        } else {
            $wd = (Resolve-Path -LiteralPath $s.WorkingDirectory).Path
            if ($wd -ne $repoResolved) {
                $issues.Add("Werkmap wijkt af van repo-root: $wd")
            }
        }
    } else {
        $issues.Add('WorkingDirectory is leeg')
    }
    $targetLeaf = Split-Path $s.TargetPath -Leaf
    if ($targetLeaf -match '^(cmd|wt|WindowsTerminal)\.exe$') {
        $quotedBat = Get-HermesBatPathFromShortcutArguments -Arguments $s.Arguments
        if (-not $quotedBat) {
            $issues.Add('Geen call ""pad.bat"" in Arguments (cmd/wt)')
        } elseif ($quotedBat -notmatch '^[A-Za-z]:\\|^\\\\') {
            $issues.Add("Relatief bat-pad in .lnk (verwacht absoluut): $quotedBat")
        }
    }
    return @{
        Ok      = ($issues.Count -eq 0)
        BatPath = $batPath
        Issues  = $issues
    }
}

function Get-HermesWindowsTerminalExe {
    $wt = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\wt.exe'
    if (Test-Path -LiteralPath $wt) { return $wt }
    $cmd = Get-Command wt.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Set-HermesStartShellShortcut {
    <#
    .SYNOPSIS
        Start-snelkoppeling: Windows Terminal + start_hermes(.bat|_full.bat) (zelfde keten als repo-root).
        Fallback zonder wt: cmd /k + start bat (venster blijft open bij fout; geen flits door cmd /c).
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$ShortcutPath,
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$IconIcoPath,
        [string]$Description = '',
        [ValidateSet('minimal', 'full')]
        [string]$LaunchProfile = 'minimal'
    )
    if (-not $PSCmdlet.ShouldProcess($ShortcutPath, 'Create', 'Hermes start shortcut')) { return $false }

    $repo = (Resolve-Path -LiteralPath $RepoRoot).Path
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'launcher_config.ps1'))) {
        throw 'launcher_config.ps1 ontbreekt naast HermesIconGeneratorInvoke.ps1'
    }
    . (Join-Path $PSScriptRoot 'launcher_config.ps1')
    $startRel = Get-HermesStartLauncherRelativePath -RepoRoot $repo -LaunchProfile $LaunchProfile
    $startBat = Join-Path $repo $startRel
    if (-not (Test-Path -LiteralPath $startBat)) { return $false }

    $iconLoc = Get-HermesShellShortcutIconLocation -IcoPath $IconIcoPath
    if (-not $iconLoc) { return $false }

    if (Test-Path -LiteralPath $ShortcutPath) {
        Remove-Item -LiteralPath $ShortcutPath -Force -ErrorAction SilentlyContinue
    }

    $startBatFull = (Resolve-Path -LiteralPath $startBat).Path
    $wt = Get-HermesWindowsTerminalExe
    $cmdExe = Join-Path $env:SystemRoot 'System32\cmd.exe'

    $wsh = New-Object -ComObject WScript.Shell
    $sc = $wsh.CreateShortcut($ShortcutPath)
    if ($wt) {
        $sc.TargetPath = $wt
        $sc.Arguments = ('-M -d "{0}" {1} /k call "{2}"' -f $repo, $cmdExe, $startBatFull)
    } else {
        $sc.TargetPath = $cmdExe
        $sc.Arguments = Get-HermesCmdShortcutArgumentLine -BatchPath $startBatFull -KeepWindowOpen
    }
    $sc.WorkingDirectory = $repo
    $sc.WindowStyle = 1
    $sc.IconLocation = $iconLoc
    if ($Description) { $sc.Description = $Description }
    $sc.Save()
    return $true
}

function Set-HermesShellShortcut {
    <#
    .SYNOPSIS
        Snelkoppeling voor windows\*.lnk: cmd.exe /c + multi-size .ico (Verkenner toont anders bat-document).
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$ShortcutPath,
        [Parameter(Mandatory)][string]$TargetBatPath,
        [Parameter(Mandatory)][string]$IconIcoPath,
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [string]$Description = '',
        [switch]$KeepCmdWindowOpen
    )
    if (-not (Test-Path -LiteralPath $TargetBatPath)) { return $false }
    if (-not $PSCmdlet.ShouldProcess($ShortcutPath, 'Create', 'Hermes shortcut')) { return $false }

    if (Test-Path -LiteralPath $ShortcutPath) {
        Remove-Item -LiteralPath $ShortcutPath -Force -ErrorAction SilentlyContinue
    }

    $batFull = (Resolve-Path -LiteralPath $TargetBatPath).Path
    $workFull = if (Test-Path -LiteralPath $WorkingDirectory) {
        (Resolve-Path -LiteralPath $WorkingDirectory).Path
    } else {
        $WorkingDirectory
    }
    $iconLoc = Get-HermesShellShortcutIconLocation -IcoPath $IconIcoPath
    if (-not $iconLoc) { return $false }

    $wt = Get-HermesWindowsTerminalExe
    $cmdExe = Join-Path $env:SystemRoot 'System32\cmd.exe'
    $wsh = New-Object -ComObject WScript.Shell
    $sc = $wsh.CreateShortcut($ShortcutPath)
    if ($wt) {
        $sc.TargetPath = $wt
        $sc.Arguments = Get-HermesWtShortcutArgumentLine -WorkingDirectory $workFull -BatchPath $batFull `
            -KeepWindowOpen:$KeepCmdWindowOpen
    } else {
        $sc.TargetPath = $cmdExe
        $sc.Arguments = Get-HermesCmdShortcutArgumentLine -BatchPath $batFull -KeepWindowOpen:$KeepCmdWindowOpen
    }
    $sc.WorkingDirectory = $workFull
    $sc.WindowStyle = 1
    $sc.IconLocation = $iconLoc
    if ($Description) { $sc.Description = $Description }
    $sc.Save()

    $verify = $wsh.CreateShortcut($ShortcutPath)
    if ($verify.IconLocation -ne $iconLoc) {
        throw "IconLocation niet gezet op $ShortcutPath (verwacht $iconLoc, got $($verify.IconLocation))"
    }
    return $true
}

function Set-HermesTaskbarPinShortcut {
    <#
    .SYNOPSIS
        Zelfde als Set-HermesShellShortcut (wt.exe + call bat); taakbalk-pin = kopie van windows\ .lnk.
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$ShortcutPath,
        [Parameter(Mandatory)][string]$TargetBatPath,
        [Parameter(Mandatory)][string]$IconIcoPath,
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [string]$Description = '',
        [switch]$KeepCmdWindowOpen
    )
    return Set-HermesShellShortcut -ShortcutPath $ShortcutPath -TargetBatPath $TargetBatPath `
        -IconIcoPath $IconIcoPath -WorkingDirectory $WorkingDirectory `
        -Description $Description -KeepCmdWindowOpen:$KeepCmdWindowOpen
}

function Get-HermesWindowsShellIcoLocation {
    <#
    .SYNOPSIS
        Pad voor WScript.Shell IconLocation (snelkoppelingen).
    .NOTES
        Gegenereerde Hermes-.ico: **32bpp DIB + alpha** in ICO, met ontbrekende **AND**-bytes aangevuld na Pillow (anders zwart vlak in Shell); index **0** voor `IconLocation`.
    #>
    param(
        [Parameter(Mandatory)][string]$IcoPath
    )
    if (-not (Test-Path -LiteralPath $IcoPath)) {
        return $null
    }
    return ($IcoPath + ',0')
}

function Invoke-HermesColoredIconsFromPng {
    param(
        [Parameter(Mandatory)][string]$IconGeneratorPy,
        [switch]$Quiet
    )
    if (-not (Test-Path -LiteralPath $IconGeneratorPy)) { return $false }

    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $ok = $false
    try {
        $condaExe = $null
        foreach ($p in @(
                (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
                (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe'),
                (Join-Path ${env:ProgramData} 'miniconda3\Scripts\conda.exe'),
                (Join-Path ${env:ProgramData} 'anaconda3\Scripts\conda.exe')
            )) {
            if ($p -and (Test-Path -LiteralPath $p)) {
                $condaExe = $p
                break
            }
        }
        if ($condaExe) {
            if ($Quiet) {
                $null = & $condaExe run -n hermes-env --no-capture-output python $IconGeneratorPy 2>&1
            } else {
                & $condaExe run -n hermes-env --no-capture-output python $IconGeneratorPy
            }
            if ($LASTEXITCODE -eq 0) { $ok = $true }
        }
        if (-not $ok) {
            foreach ($pair in @(
                    @{ Exe = 'py'; Args = @('-3.12') },
                    @{ Exe = 'py'; Args = @('-3.11') },
                    @{ Exe = 'py'; Args = @('-3') },
                    @{ Exe = 'py'; Args = @() },
                    @{ Exe = 'python'; Args = @() }
                )) {
                if (-not (Get-Command $pair.Exe -ErrorAction SilentlyContinue)) { continue }
                $argList = @()
                if ($pair.Args.Count -gt 0) { $argList = $pair.Args }
                $argList += $IconGeneratorPy
                & $pair.Exe @argList 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    $ok = $true
                    break
                }
            }
        }
    } finally {
        $ErrorActionPreference = $prevEap
    }
    if (-not $ok -and -not $Quiet) {
        Write-Host '  [WARN] Icoon-generator mislukt (Pillow ontbreekt?). Handmatig: python windows/tools/generate_colored_hermes_icons.py' -ForegroundColor Yellow
    }
    return $ok
}

function Test-HermesWindowsIconRegenNeeded {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$WindowsDir
    )
    $pngA = Join-Path $RepoRoot 'assets\Hermes_logo.png'
    $pngB = Join-Path $RepoRoot 'assets\hermes_logo.png'
    $png = $null
    if (Test-Path -LiteralPath $pngA) { $png = $pngA }
    elseif (Test-Path -LiteralPath $pngB) { $png = $pngB }
    else { return $false }

    $icoGen = Join-Path $WindowsDir 'tools\generate_colored_hermes_icons.py'
    if (-not (Test-Path -LiteralPath $icoGen)) { return $false }

    $icoMain = Join-Path $WindowsDir 'hermes_logo.ico'
    if (-not (Test-Path -LiteralPath $icoMain)) { return $true }

    $iMain = Get-Item -LiteralPath $icoMain
    $iPng = Get-Item -LiteralPath $png
    if ($iPng.LastWriteTime -gt $iMain.LastWriteTime) { return $true }

    # Alleen echte desync: gekleurde .ico's zijn ná generate vaak 0-2 s nieuwer dan main; dat is normaal.
    $skewSec = 4
    foreach ($leaf in @('hermes_logo_backup.ico', 'hermes_logo_restore.ico', 'hermes_logo_update.ico', 'hermes_logo_setup.ico', 'hermes_taskbar_white.ico')) {
        $p2 = Join-Path $WindowsDir $leaf
        if (-not (Test-Path -LiteralPath $p2)) { continue }
        $age = ((Get-Item -LiteralPath $p2).LastWriteTime - $iMain.LastWriteTime).TotalSeconds
        if ($age -gt $skewSec) {
            return $true
        }
    }
    return $false
}

function Get-HermesTaskbarRoleIconPath {
    <#
    .SYNOPSIS
        Pad naar .ico per taakbalk-rol. Update = hermes_logo_update.ico (wit/zilver); niet hermes_taskbar_white in .lnk.
    #>
    param(
        [Parameter(Mandatory)]
        [ValidateSet('Start', 'StartFast', 'Setup', 'OpenSetup', 'Update', 'Backup', 'Restore', 'Rag', 'Obsidian')]
        [string]$Role,
        [Parameter(Mandatory)][string]$WindowsDir
    )
    $leaf = switch ($Role) {
        'StartFast' { 'hermes_logo_update.ico' }
        'Update' { 'hermes_logo_update.ico' }
        'Setup' { 'hermes_logo_setup.ico' }
        'OpenSetup' { 'hermes_logo_setup.ico' }
        'Obsidian' { 'hermes_logo_restore.ico' }
        'Restore' { 'hermes_logo_restore.ico' }
        'Backup' { 'hermes_logo_backup.ico' }
        'Rag' { 'hermes_logo.ico' }
        default { 'hermes_logo.ico' }
    }
    $path = Join-Path $WindowsDir $leaf
    if (Test-Path -LiteralPath $path) { return $path }
    $main = Join-Path $WindowsDir 'hermes_logo.ico'
    if (Test-Path -LiteralPath $main) { return $main }
    return $null
}

function Get-HermesTaskbarRoleIconLocation {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('Start', 'StartFast', 'Setup', 'OpenSetup', 'Update', 'Backup', 'Restore', 'Rag', 'Obsidian')]
        [string]$Role,
        [Parameter(Mandatory)][string]$WindowsDir
    )
    $path = Get-HermesTaskbarRoleIconPath -Role $Role -WindowsDir $WindowsDir
    if (-not $path) { return $null }
    return (Get-HermesWindowsShellIcoLocation -IcoPath $path)
}
