# Hermes Agent: Desktop Shortcut Creator
param(
    # Optioneel: repo-root (map met pyproject.toml). CREATE_DESKTOP_SHORTCUT.bat zet dit door
    # zodat dit script ook werkt als het vanuit een tijdelijke kopie wordt aangeroepen.
    [string] $RepoRoot = '',
    [switch] $NoPause
)

$ErrorActionPreference = 'Stop'

function Get-ScriptDirectory {
    if ($PSScriptRoot) { return $PSScriptRoot }
    if ($MyInvocation.MyCommand.Path) { return (Split-Path -Parent $MyInvocation.MyCommand.Path) }
    return (Get-Location).Path
}

function Find-HermesAgentRepoRoot {
    param([string] $StartDir)
    if (-not (Test-Path -LiteralPath $StartDir)) { return $null }
    $d = (Get-Item -LiteralPath $StartDir).FullName.TrimEnd('\')
    for ($i = 0; $i -lt 20; $i++) {
        $py = Join-Path $d 'pyproject.toml'
        $win = Join-Path $d 'windows'
        if ((Test-Path -LiteralPath $py) -and (Test-Path -LiteralPath $win)) {
            return $d
        }
        $par = Split-Path -Path $d -Parent
        if (-not $par -or ($par -eq $d)) { break }
        $d = $par
    }
    return $null
}

$scriptDir = Get-ScriptDirectory

$resolvedRepo = $null
if ($RepoRoot -and $RepoRoot.Trim()) {
    $rp = $RepoRoot.Trim()
    if (Test-Path -LiteralPath $rp) {
        $resolvedRepo = (Get-Item -LiteralPath $rp).FullName.TrimEnd('\')
    } else {
        Write-Host ('[WARNING] ' + '-RepoRoot bestaat niet: ' + $rp) -ForegroundColor Yellow
    }
}

if (-not $resolvedRepo) {
    if ((Split-Path -Leaf $scriptDir) -ieq 'windows') {
        $resolvedRepo = (Get-Item -LiteralPath (Join-Path $scriptDir '..')).FullName.TrimEnd('\')
    }
}

if (-not $resolvedRepo) {
    $resolvedRepo = Find-HermesAgentRepoRoot -StartDir $scriptDir
}

if (-not $resolvedRepo) {
    $resolvedRepo = Find-HermesAgentRepoRoot -StartDir (Get-Location).Path
}

if (-not $resolvedRepo) {
    Write-Host '[ERROR] Kon hermes-agent repo-root niet bepalen (geen pyproject.toml + windows\ gevonden).' -ForegroundColor Red
    Write-Host 'Start CREATE_DESKTOP_SHORTCUT.bat vanuit deze map, of geef -RepoRoot door.' -ForegroundColor Gray
    exit 1
}

$windowsDir = Join-Path $resolvedRepo 'windows'
$iconPath = Join-Path $windowsDir 'hermes_logo.ico'
. (Join-Path $windowsDir 'HermesIconGeneratorInvoke.ps1')
. (Join-Path $windowsDir 'launcher_config.ps1')
$batchLeaf = Get-HermesStartLauncherRelativePath -RepoRoot $resolvedRepo
$batchPath = Join-Path $resolvedRepo $batchLeaf
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Hermes Agent.lnk'

Write-Host '================================================' -ForegroundColor Cyan
Write-Host '  Hermes Agent: Shortcut Creator' -ForegroundColor Cyan
Write-Host '================================================' -ForegroundColor Cyan
Write-Host ''

if (-not (Test-Path -LiteralPath $batchPath)) {
    Write-Host ('[WARNING] ' + 'Start-launcher niet op repo-root: ' + $batchPath + ' (HERMES_START_BAT / split / start_hermes)') -ForegroundColor Yellow
}

if (-not (Test-Path -LiteralPath $iconPath)) {
    Write-Host ('[WARNING] ' + 'hermes_logo.ico niet gevonden: ' + $iconPath) -ForegroundColor Yellow
    Write-Host 'Er wordt een standaard icoon gebruikt.' -ForegroundColor Gray
    $iconPath = 'cmd.exe'
}

try {
    $deskIco = Join-Path $windowsDir 'hermes_logo.ico'
    if (-not (Test-Path -LiteralPath $deskIco)) { $deskIco = $iconPath }
    if (Set-HermesStartShellShortcut -ShortcutPath $shortcutPath -RepoRoot $resolvedRepo `
            -IconIcoPath $deskIco -Description 'Hermes Agent (volledig: SOUL, Docker, dashboard)' `
            -LaunchProfile full) {
        Write-Host '[SUCCESS] Snelkoppeling aangemaakt op je Bureaublad!' -ForegroundColor Green
        Write-Host '[OK] Hermes Agent.lnk -> start_hermes.bat (profiel: full)' -ForegroundColor Green
    } else {
        throw 'Set-HermesStartShellShortcut mislukt'
    }

    $fastLnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Hermes Agent (snel).lnk'
    $fastIco = Join-Path $windowsDir 'hermes_logo_update.ico'
    if (-not (Test-Path -LiteralPath $fastIco)) { $fastIco = $deskIco }
    $fastBat = Join-Path $resolvedRepo 'start_hermes_minimal.bat'
    if ((Test-Path -LiteralPath $fastBat) -and (Set-HermesStartShellShortcut -ShortcutPath $fastLnk -RepoRoot $resolvedRepo `
            -IconIcoPath $fastIco -Description 'Hermes snel (minimal, alleen chat)' -LaunchProfile minimal)) {
        Write-Host '[OK] Hermes Agent (snel).lnk -> start_hermes_minimal.bat' -ForegroundColor Green
    }

    $logoBat = Join-Path $windowsDir 'Hermes_met_logo.bat'
    if (Test-Path -LiteralPath $logoBat) {
        $logoLnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Hermes Agent (met logo).lnk'
        Set-HermesShellShortcut -ShortcutPath $logoLnk -TargetBatPath $logoBat `
            -IconIcoPath (Join-Path $windowsDir 'hermes_logo.ico') -WorkingDirectory $resolvedRepo `
            -Description 'Hermes Agent - ASCII-logo, daarna start_hermes.bat' -KeepCmdWindowOpen | Out-Null
        Write-Host '[OK] Hermes Agent (met logo).lnk (optioneel)' -ForegroundColor Green
    }

    $taskbarPs1 = Join-Path $windowsDir 'create_taskbar_shortcuts.ps1'
    if (Test-Path -LiteralPath $taskbarPs1) {
        Write-Host 'Taakbalk-snelkoppelingen in windows\ bijwerken...' -ForegroundColor Gray
        & $taskbarPs1 -RepoRoot $resolvedRepo -OutDir $windowsDir
    }
} catch {
    Write-Host ('[ERROR] ' + 'Kon snelkoppeling niet aanmaken: ' + $($_.Exception.Message)) -ForegroundColor Red
    exit 1
}

Write-Host ''
if (-not $NoPause) { pause }
