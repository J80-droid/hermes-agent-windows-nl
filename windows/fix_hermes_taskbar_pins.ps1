#requires -Version 5.1
# Vernieuwt Hermes-taakbalk-pins: cmd.exe-wrapper + gekleurde .ico (geen hermes_taskbar_white in .lnk).
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $RepoRoot.Trim()) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptDir '..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}

. (Join-Path $scriptDir 'HermesIconGeneratorInvoke.ps1')
. (Join-Path $scriptDir 'launcher_config.ps1')

function Clear-HermesShellIconCache {
    $ie4u = Join-Path $env:SystemRoot 'System32/ie4uinit.exe'
    if (-not (Test-Path -LiteralPath $ie4u)) { return }
    Start-Process -FilePath $ie4u -ArgumentList '-show' -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
    Start-Process -FilePath $ie4u -ArgumentList '-ClearIconCache' -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
}

function Repair-HermesBatShortcut {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [string]$LnkPath,
        [string]$BatPath,
        [string]$RepoRoot,
        [string]$IconLocation
    )
    if (-not (Test-Path -LiteralPath $LnkPath)) { return }
    if (-not $PSCmdlet.ShouldProcess($LnkPath, 'Update', 'Hermes shortcut')) { return }
    if (-not (Test-Path -LiteralPath $BatPath)) { return }
    $w = New-Object -ComObject WScript.Shell
    $s = $w.CreateShortcut($LnkPath)
    $s.TargetPath = Join-Path $env:SystemRoot 'System32/cmd.exe'
    $s.Arguments = '/c "' + $BatPath + '"'
    $s.WorkingDirectory = $RepoRoot
    if ($IconLocation) { $s.IconLocation = $IconLocation }
    $s.Save()
}

function Update-PinnedHermesShortcut {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [string]$SourceLnk,
        [string]$PinnedDir
    )
    if (-not (Test-Path -LiteralPath $SourceLnk)) { return $false }
    if (-not (Test-Path -LiteralPath $PinnedDir)) { return $false }
    $name = [IO.Path]::GetFileName($SourceLnk)
    $dest = Join-Path $PinnedDir $name
    if (-not $PSCmdlet.ShouldProcess($dest, 'Update', 'Pinned taskbar shortcut')) { return $false }
    Copy-Item -LiteralPath $SourceLnk -Destination $dest -Force
    return $true
}

$createPs1 = Join-Path $scriptDir 'create_taskbar_shortcuts.ps1'
if (-not (Test-Path -LiteralPath $createPs1)) {
    Write-Host "[ERROR] Ontbreekt: $createPs1" -ForegroundColor Red
    exit 1
}

& $createPs1 -RepoRoot $RepoRoot -OutDir $scriptDir -Quiet:$Quiet

$startBatFull = Join-Path $RepoRoot (Get-HermesStartLauncherRelativePath -RepoRoot $RepoRoot)

$repairRows = @(
    , @('Hermes - update - naar taakbalk slepen.lnk', 'UPDATE_HERMES.bat', 'Update')
    , @('Hermes - setup Windows - naar taakbalk slepen.lnk', 'setup_hermes_windows.bat', 'Setup')
    , @('Start Hermes - naar taakbalk slepen.lnk', '', 'Start')
    , @('Hermes - backup - naar taakbalk slepen.lnk', 'MANAGE_BACKUPS.bat', 'Backup')
    , @('Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk', 'restore_local_assets.bat', 'Restore')
    , @('Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk', 'RAG_KNOWLEDGE_UPDATE_NIGHT.bat', 'Rag')
)

foreach ($row in $repairRows) {
    $lnk = Join-Path $scriptDir $row[0]
    if (-not (Test-Path -LiteralPath $lnk)) { continue }
    $batPath = if ($row[1]) { Join-Path $scriptDir $row[1] } else { $startBatFull }
    if (-not (Test-Path -LiteralPath $batPath)) { continue }
    $iconLoc = Get-HermesTaskbarRoleIconLocation -Role $row[2] -WindowsDir $scriptDir
    Repair-HermesBatShortcut -LnkPath $lnk -BatPath $batPath -RepoRoot $RepoRoot -IconLocation $iconLoc
}

$openBat = Join-Path $scriptDir 'OPEN_SETUP.bat'
if (Test-Path -LiteralPath $openBat) {
    $openIcon = Get-HermesTaskbarRoleIconLocation -Role 'OpenSetup' -WindowsDir $scriptDir
    Repair-HermesBatShortcut -LnkPath (Join-Path $scriptDir 'Hermes - Open Setup - naar taakbalk slepen.lnk') `
        -BatPath $openBat -RepoRoot $RepoRoot -IconLocation $openIcon
}

$pinnedDir = Join-Path $env:APPDATA (Join-Path 'Microsoft' (Join-Path 'Internet Explorer' (Join-Path 'Quick Launch' (Join-Path 'User Pinned' 'TaskBar'))))
$toPin = @(
    'Hermes - update - naar taakbalk slepen.lnk',
    'Hermes - setup Windows - naar taakbalk slepen.lnk',
    'Start Hermes - naar taakbalk slepen.lnk',
    'Hermes - backup - naar taakbalk slepen.lnk'
)

if (Test-Path -LiteralPath $pinnedDir) {
    foreach ($leaf in $toPin) {
        $src = Join-Path $scriptDir $leaf
        if (Update-PinnedHermesShortcut -SourceLnk $src -PinnedDir $pinnedDir) {
            if (-not $Quiet) {
                Write-Host "  [OK] Taakbalk-pin bijgewerkt: $leaf" -ForegroundColor Green
            }
        }
    }
} elseif (-not $Quiet) {
    Write-Host '  [INFO] Geen map User Pinned/TaskBar - pin handmatig via rechtsklik.' -ForegroundColor Gray
}

Clear-HermesShellIconCache

if (-not $Quiet) {
    Write-Host ''
    Write-Host 'Icoonnen: setup/start/backup/RAG = goud (hermes_logo.ico), update = oranje, restore = cyaan.' -ForegroundColor Cyan
    Write-Host 'Blijft een oud H zichtbaar: pin losmaken, .lnk opnieuw vastmaken (niet .bat slepen).' -ForegroundColor Gray
}

exit 0
