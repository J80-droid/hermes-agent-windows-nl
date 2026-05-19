# Hermes Agent: Desktop Shortcut Creator
param(
    # Optioneel: repo-root (map met pyproject.toml). CREATE_DESKTOP_SHORTCUT.bat zet dit door
    # zodat dit script ook werkt als het vanuit een tijdelijke kopie wordt aangeroepen.
    [string] $RepoRoot = ''
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
        Write-Host "[WARNING] -RepoRoot bestaat niet: $rp" -ForegroundColor Yellow
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
$hermesDir = $resolvedRepo
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Hermes Agent.lnk'

Write-Host '================================================' -ForegroundColor Cyan
Write-Host '  Hermes Agent: Shortcut Creator' -ForegroundColor Cyan
Write-Host '================================================' -ForegroundColor Cyan
Write-Host ''

if (-not (Test-Path -LiteralPath $batchPath)) {
    Write-Host "[WARNING] Start-launcher niet op repo-root: $batchPath (HERMES_START_BAT / split / start_hermes)" -ForegroundColor Yellow
}

if (-not (Test-Path -LiteralPath $iconPath)) {
    Write-Host "[WARNING] hermes_logo.ico niet gevonden: $iconPath" -ForegroundColor Yellow
    Write-Host 'Er wordt een standaard icoon gebruikt.' -ForegroundColor Gray
    $iconPath = 'cmd.exe'
}

try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    # TRICK: Prefix with cmd /c to allow taskbar pinning
    $Shortcut.TargetPath = 'cmd.exe'
    $Shortcut.Arguments = "/c `"$batchPath`""
    $Shortcut.WorkingDirectory = $hermesDir
    if ($iconPath -match '\.ico$') {
        $iconPath = Get-HermesWindowsShellIcoLocation -IcoPath $iconPath
    }
    $Shortcut.IconLocation = $iconPath
    $Shortcut.Description = 'Launch the Hermes AI Agent'
    $Shortcut.Save()
    Write-Host '[SUCCESS] Snelkoppeling aangemaakt op je Bureaublad!' -ForegroundColor Green

    $taskbarPs1 = Join-Path $windowsDir 'create_taskbar_shortcuts.ps1'
    if (Test-Path -LiteralPath $taskbarPs1) {
        Write-Host 'Taakbalk-snelkoppelingen in windows\ bijwerken...' -ForegroundColor Gray
        & $taskbarPs1 -RepoRoot $resolvedRepo -OutDir $windowsDir
    }
} catch {
    Write-Host "[ERROR] Kon snelkoppeling niet aanmaken: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ''
pause
