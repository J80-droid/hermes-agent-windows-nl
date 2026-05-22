#requires -Version 5.1
# INSTITUTIONEEL: enige setup-PS1 om te bewerken. Kopieer NOOIT naar windows/setup_hermes_windows.ps1
# (die blijft een dunne wrapper in git; VERIFY_WINDOWS_CHAIN.bat faalt bij volledige kopie).
<#
.SYNOPSIS
  Windows-setup: schrijft lokale bestanden onder <repo>/windows/ (gitignored) en
  optioneel snelkoppelingen (Desktop + taakbalk-stijl in windows/).

.DESCRIPTION
  - Maakt windows/Hermes_met_logo.bat (ANSI wit logo; roept launch_hermes.bat aan).
  - Schrijft windows/setup_hermes_windows.bat en windows/hermes_update.bat.
  - Genereert hermes_taskbar_white.ico (zilver/wit monogram; niet voor taakbalk-.lnk).
  - Hermes - setup Windows / Hermes - update / **Open Setup** (naar taakbalk slepen).lnk in windows/.
  - Minimaal launch_hermes.bat alleen als het nog ontbreekt (tenzij -ForceLaunchBat).
  - Desktop: **Hermes Agent.lnk** + **Hermes Open Setup.lnk** tenzij -NoShortcut.

  Draai altijd de **.bat** vanuit Explorer (dubbelklik op .ps1 gebruikt vaak Restricted policy).

  - Optioneel: volledige **hermes setup --full** na de Windows-bestanden via **OPEN_SETUP.bat**
    ^(zelfde cmd + zelfde Conda/.venv-Python als launch_hermes.bat^). Dubbelklik: **windows/OPEN_SETUP.bat**.

  Triggers: -FullSetup, HERMES_SETUP_FULL_SETUP=1, of op setup-batch: **--full-setup**.

  Na interactieve setup start **Hermes automatisch** in een nieuw cmd-venster (Hermes_met_logo.bat),
  tenzij de omgeving **HERMES_SETUP_NO_LAUNCH** is gezet.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$RepoRoot = "",
    [switch]$NoShortcut,
    [switch]$NoTaskbarLinks,
    [switch]$ForceLogoBat,
    [switch]$ForceLaunchBat,
    [switch]$FullSetup
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
    param([string]$Explicit)
    if ($Explicit -and (Test-Path -LiteralPath $Explicit)) {
        return (Resolve-Path -LiteralPath $Explicit).Path
    }
    $here = $PSScriptRoot
    $candidate = Resolve-Path (Join-Path $here "..\..") | Select-Object -ExpandProperty Path
    if (Test-Path -LiteralPath (Join-Path $candidate "cli.py")) {
        return $candidate
    }
    throw "Repo-root niet gevonden. Geef -RepoRoot mee (map met cli.py)."
}

function Get-HermesSetupBatTemplateContent {
    param([Parameter(Mandatory)][string]$TemplateLeaf)
    $templatePath = Join-Path $PSScriptRoot (Join-Path 'bat-templates' $TemplateLeaf)
    if (-not (Test-Path -LiteralPath $templatePath)) {
        throw "Ontbrekende bat-template: $templatePath"
    }
    return (Get-Content -LiteralPath $templatePath -Raw -Encoding ASCII)
}

function Write-LogoBat {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$WindowsDir
    )
    $path = Join-Path $WindowsDir "Hermes_met_logo.bat"
    $bat = Get-HermesSetupBatTemplateContent -TemplateLeaf 'Hermes_met_logo.bat.template'
    if (-not $PSCmdlet.ShouldProcess($path, 'Create', 'Logo launcher batch')) { return }
    Set-Content -LiteralPath $path -Value $bat -Encoding ASCII
}

function Write-MinimalLaunchBat {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$WindowsDir
    )
    $path = Join-Path $WindowsDir "launch_hermes.bat"
    $bat = Get-HermesSetupBatTemplateContent -TemplateLeaf 'launch_hermes.bat.template'
    if (-not $PSCmdlet.ShouldProcess($path, 'Create', 'Minimal launch_hermes.bat')) { return }
    Set-Content -LiteralPath $path -Value $bat -Encoding ASCII
}

function Get-HermesDesktopShortcutIcon {
    param(
        [Parameter(Mandatory)][string]$WindowsDir,
        [string]$RepoRoot = ''
    )
    $icoGen = Join-Path $WindowsDir 'tools/generate_colored_hermes_icons.py'
    if ((Test-Path -LiteralPath $icoGen) -and $RepoRoot) {
        $invoke = Join-Path $WindowsDir 'HermesIconGeneratorInvoke.ps1'
        if (Test-Path -LiteralPath $invoke) {
            . $invoke
            if (Test-HermesWindowsIconRegenNeeded -RepoRoot $RepoRoot -WindowsDir $WindowsDir) {
                [void](Invoke-HermesColoredIconsFromPng -IconGeneratorPy $icoGen -Quiet)
            }
        }
    }
    $main = Join-Path $WindowsDir 'hermes_logo.ico'
    if (Test-Path -LiteralPath $main) {
        if ($WhatIfPreference) { return ($main + ',0') }
        . (Join-Path $WindowsDir 'HermesIconGeneratorInvoke.ps1')
        return (Get-HermesWindowsShellIcoLocation -IcoPath $main)
    }
    Write-Warning 'hermes_logo.ico ontbreekt - draai: python windows/tools/generate_colored_hermes_icons.py'
    return ($env:SystemRoot + '\System32\imageres.dll,1')
}

function Get-HermesSetupShortcutIconLocation {
    param([Parameter(Mandatory)][string]$WindowsDir)
    $invoke = Join-Path $WindowsDir 'HermesIconGeneratorInvoke.ps1'
    if (-not (Test-Path -LiteralPath $invoke)) {
        return (Get-HermesDesktopShortcutIcon -WindowsDir $WindowsDir)
    }
    . $invoke
    $loc = Get-HermesTaskbarRoleIconLocation -Role 'OpenSetup' -WindowsDir $WindowsDir
    if ($loc) { return $loc }
    return (Get-HermesDesktopShortcutIcon -WindowsDir $WindowsDir)
}

function New-ShellShortcut {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$LnkPath,
        [string]$TargetPath,
        [string]$Arguments,
        [string]$WorkDir,
        [string]$IconLocation,
        [string]$Description
    )
    if (-not $PSCmdlet.ShouldProcess($LnkPath, 'Create', 'Shell shortcut')) { return }
    # Taakbalk (Win10/11): .bat als TargetPath → Shell negeert vaak IconLocation (generiek H/cmd-icoon).
    $launchTarget = $TargetPath
    $launchArgs = $Arguments
    if ($TargetPath -match '\.bat$' -and -not $Arguments.Trim()) {
        $launchTarget = Join-Path $env:SystemRoot 'System32\cmd.exe'
        $launchArgs = '/c "' + $TargetPath + '"'
    }
    $w = New-Object -ComObject WScript.Shell
    $s = $w.CreateShortcut($LnkPath)
    $s.TargetPath = $launchTarget
    $s.Arguments = $launchArgs
    $s.WorkingDirectory = $WorkDir
    $s.WindowStyle = 1
    if ($IconLocation) { $s.IconLocation = $IconLocation }
    if ($Description) { $s.Description = $Description }
    $s.Save()
}

function Write-WindowsSetupCmdBat {
    [CmdletBinding(SupportsShouldProcess)]
    param([Parameter(Mandatory)][string]$WindowsDir)
    $path = Join-Path $WindowsDir "setup_hermes_windows.bat"
    $bat = Get-HermesSetupBatTemplateContent -TemplateLeaf 'setup_hermes_windows.bat.template'
    if (-not $PSCmdlet.ShouldProcess($path, 'Create', 'setup_hermes_windows.bat')) { return }
    Set-Content -LiteralPath $path -Value $bat -Encoding ASCII
}

function Write-HermesUpdateCmdBat {
    [CmdletBinding(SupportsShouldProcess)]
    param([Parameter(Mandatory)][string]$WindowsDir)
    $path = Join-Path $WindowsDir "hermes_update.bat"
    $bat = Get-HermesSetupBatTemplateContent -TemplateLeaf 'hermes_update.bat.template'
    if ($PSCmdlet.ShouldProcess($path, 'Create', 'hermes_update.bat')) {
        Set-Content -LiteralPath $path -Value $bat -Encoding ASCII
    }
}

function Invoke-HermesFullSetupWizard {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )
    if (-not $PSCmdlet.ShouldProcess($RepoRoot, 'Run', 'hermes setup --full')) { return 0 }
    $hermesExe = $null
    foreach ($name in @('hermes.exe', 'hermes.cmd')) {
        $p = Join-Path $RepoRoot (Join-Path '.venv\Scripts' $name)
        if (Test-Path -LiteralPath $p) {
            $hermesExe = $p
            break
        }
    }
    if (-not $hermesExe) {
        try {
            $cmd = Get-Command hermes -ErrorAction Stop
            if ($cmd.Path) { $hermesExe = $cmd.Path }
        } catch {
            $null = $_.Exception.Message
        }
    }
    if (-not $hermesExe -or -not (Test-Path -LiteralPath $hermesExe)) {
        Write-Host "[ERROR] hermes-CLI niet gevonden (.venv\Scripts noch PATH). Installeer deps / venv, daarna: hermes setup --full" -ForegroundColor Red
        return 1
    }
    Write-Host ""
    Write-Host "[Hermes] Start installatiewizard (hermes setup --full) ..." -ForegroundColor Cyan
    Push-Location $RepoRoot
    try {
        & $hermesExe setup --full
        $code = $LASTEXITCODE
        if ($null -eq $code) { return 0 }
        return $code
    } finally {
        Pop-Location
    }
}

function New-DesktopShortcut {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$TargetBat,
        [Parameter(Mandatory)][string]$WorkDir,
        [Parameter(Mandatory)][string]$IconLocation
    )
    $desktop = [Environment]::GetFolderPath("Desktop")
    if (-not $desktop) { return }
    $lnkPath = Join-Path $desktop "Hermes Agent.lnk"
    New-ShellShortcut -LnkPath $lnkPath -TargetPath "cmd.exe" -Arguments ('/k "' + $TargetBat + '"') `
        -WorkDir $WorkDir -IconLocation $IconLocation `
        -Description "Hermes Agent - Windows launcher (logo)" -WhatIf:$WhatIfPreference
}

$root = Resolve-RepoRoot -Explicit $RepoRoot
$win = Join-Path $root "windows"

if (-not $WhatIfPreference) {
    New-Item -ItemType Directory -Path $win -Force | Out-Null
}

$iconLoc = Get-HermesDesktopShortcutIcon -WindowsDir $win -RepoRoot $root

Write-WindowsSetupCmdBat -WindowsDir $win -WhatIf:$WhatIfPreference
if (-not $WhatIfPreference) { Write-Host ('[OK] ' + (Join-Path $win 'setup_hermes_windows.bat')) -ForegroundColor Green }

$openSetupSrc = Join-Path $PSScriptRoot "OPEN_SETUP.bat"
$openSetupDst = Join-Path $win "OPEN_SETUP.bat"
if (-not $WhatIfPreference) {
    if (Test-Path -LiteralPath $openSetupSrc) {
        Copy-Item -LiteralPath $openSetupSrc -Destination $openSetupDst -Force
        Write-Host ('[OK] ' + $openSetupDst) -ForegroundColor Green
    } else {
        Write-Warning 'OPEN_SETUP.bat ontbreekt in scripts/windows - wizard-snelkoppeling niet gekopieerd.'
    }
}

Write-HermesUpdateCmdBat -WindowsDir $win -WhatIf:$WhatIfPreference
if (-not $WhatIfPreference) { Write-Host ('[OK] ' + (Join-Path $win 'hermes_update.bat')) -ForegroundColor Green }

$logoBat = Join-Path $win "Hermes_met_logo.bat"
$launchBat = Join-Path $win "launch_hermes.bat"

if ($ForceLogoBat -or -not (Test-Path -LiteralPath $logoBat)) {
    Write-LogoBat -WindowsDir $win -WhatIf:$WhatIfPreference
    if (-not $WhatIfPreference) { Write-Host ('[OK] Logo-launcher: ' + $logoBat) -ForegroundColor Green }
} else {
    Write-Host '[--] Logo-launcher bestaat al (gebruik -ForceLogoBat om te overschrijven).' -ForegroundColor Yellow
}

if ($ForceLaunchBat) {
    Write-MinimalLaunchBat -WindowsDir $win -WhatIf:$WhatIfPreference
    if (-not $WhatIfPreference) { Write-Host '[OK] launch_hermes.bat geschreven (-ForceLaunchBat).' -ForegroundColor Green }
} elseif (-not (Test-Path -LiteralPath $launchBat)) {
    Write-MinimalLaunchBat -WindowsDir $win -WhatIf:$WhatIfPreference
    if (-not $WhatIfPreference) { Write-Host '[OK] Minimaal launch_hermes.bat aangemaakt (was afwezig).' -ForegroundColor Green }
} else {
    Write-Host '[--] launch_hermes.bat bestaat al - niet overschreven.' -ForegroundColor Yellow
}

if (-not $NoShortcut) {
    if (Test-Path -LiteralPath $logoBat) {
        New-DesktopShortcut -TargetBat $logoBat -WorkDir $root -IconLocation $iconLoc -WhatIf:$WhatIfPreference
        if (-not $WhatIfPreference) {
            $desk = [Environment]::GetFolderPath("Desktop")
            Write-Host ('[OK] Snelkoppeling: ' + (Join-Path $desk 'Hermes Agent.lnk')) -ForegroundColor Green
        }
    } else {
        Write-Warning "Snelkoppeling overgeslagen: logo-bat ontbreekt."
    }
    $openBatWin = Join-Path $win "OPEN_SETUP.bat"
    if (Test-Path -LiteralPath $openBatWin) {
        $deskOs = [Environment]::GetFolderPath("Desktop")
        if ($deskOs) {
            $openIconLoc = Get-HermesSetupShortcutIconLocation -WindowsDir $win
            $openLnkDesk = Join-Path $deskOs "Hermes Open Setup.lnk"
            New-ShellShortcut -LnkPath $openLnkDesk -TargetPath "cmd.exe" -Arguments ('/k "' + $openBatWin + '"') `
                -WorkDir $root -IconLocation $openIconLoc `
                -Description "Hermes - volledige setup-wizard (OPEN_SETUP)" -WhatIf:$WhatIfPreference
            if (-not $WhatIfPreference) {
                Write-Host ('[OK] Snelkoppeling: ' + $openLnkDesk) -ForegroundColor Green
            }
        }
    }
}

if (-not $NoTaskbarLinks) {
    $taskbarPs1 = Join-Path $win "create_taskbar_shortcuts.ps1"
    $fixPinsPs1 = Join-Path $win "fix_hermes_taskbar_pins.ps1"
    if (Test-Path -LiteralPath $taskbarPs1) {
        if (-not $WhatIfPreference) {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $taskbarPs1 -RepoRoot $root -OutDir $win -Quiet
            Write-Host ('[OK] Taakbalk-snelkoppelingen via create_taskbar_shortcuts.ps1') -ForegroundColor Green
        } elseif ($WhatIfPreference) {
            Write-Host '[WhatIf] Zou create_taskbar_shortcuts.ps1 draaien' -ForegroundColor Yellow
        }
    }
    if (Test-Path -LiteralPath $fixPinsPs1) {
        if (-not $WhatIfPreference) {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $fixPinsPs1 -RepoRoot $root -Quiet
            Write-Host ('[OK] Taakbalk-iconen (cmd-wrapper + pins)') -ForegroundColor Green
        } elseif ($WhatIfPreference) {
            Write-Host '[WhatIf] Zou fix_hermes_taskbar_pins.ps1 draaien' -ForegroundColor Yellow
        }
    }
    $verifyTb = Join-Path $win (Join-Path 'scripts' 'verify_taskbar_shortcut_icons.ps1')
    if ((Test-Path -LiteralPath $verifyTb) -and -not $WhatIfPreference) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $verifyTb -RepoRoot $root -Quiet
        if ($LASTEXITCODE -ne 0) {
            Write-Warning 'Taakbalk-.lnk iconen wijken af — draai windows/FIX_TASKBAR_ICONS.bat'
        }
    }
}

$runHermesWizard = $FullSetup -or ($env:HERMES_SETUP_FULL_SETUP -eq '1')
$batLaunchedFromCmd = ($env:HERMES_WINDOWS_BAT_PARENT -eq '1')
if ($runHermesWizard -and -not $batLaunchedFromCmd) {
    $wizardExitCode = Invoke-HermesFullSetupWizard -RepoRoot $root -WhatIf:$WhatIfPreference
    if ($wizardExitCode -ne 0) { exit $wizardExitCode }
}

$ragExtras = Join-Path $root 'windows/scripts/install_rag_extras.ps1'
if ((Test-Path -LiteralPath $ragExtras) -and -not $WhatIfPreference) {
    Write-Host ""
    Write-Host "[INFO] RAG: pip extra [rag] + MCP lancedb-knowledge..." -ForegroundColor Cyan
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $ragExtras -RepoRoot $root -Quiet
        Write-Host "[OK] RAG-extras (pip + MCP waar mogelijk)." -ForegroundColor Green
    } catch {
        Write-Warning 'RAG-extras mislukt - handmatig: windows/scripts/install_rag_extras.ps1'
    }
}

Write-Host ""
Write-Host 'Klaar: SETUP_HERMES.bat / setup_hermes_windows.bat + taakbalk-.lnk (goud=start/RAG, groen=setup, wit=update, roze/cyaan=backup/restore).' -ForegroundColor Cyan
Write-Host 'Wizard: dubbelklik SETUP_HERMES.bat (standaard) of OPEN_SETUP.bat.' -ForegroundColor DarkGray
Write-Host 'Tip: bij verkeerd taakbalk-icoon: windows/FIX_TASKBAR_ICONS.bat' -ForegroundColor DarkGray
Write-Host 'Canoniek: scripts/windows/setup_hermes_windows.ps1 (windows/setup_hermes_windows.ps1 = wrapper).' -ForegroundColor DarkGray