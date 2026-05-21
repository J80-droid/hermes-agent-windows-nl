# Vernieuwt Hermes-taakbalk-pins: icoon + cmd.exe-wrapper (Windows negeert IconLocation bij .bat-target).
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

$createPs1 = Join-Path $scriptDir 'create_taskbar_shortcuts.ps1'
if (-not (Test-Path -LiteralPath $createPs1)) {
    Write-Host "[ERROR] Ontbreekt: $createPs1" -ForegroundColor Red
    exit 1
}

& $createPs1 -RepoRoot $RepoRoot -OutDir $scriptDir -Quiet:$Quiet

function Repair-HermesBatShortcut {
    [CmdletBinding(SupportsShouldProcess)]
    param([string]$LnkPath, [string]$BatPath, [string]$RepoRoot, [string]$IconPath)
    if (-not (Test-Path -LiteralPath $LnkPath)) { return }
    if (-not $PSCmdlet.ShouldProcess($LnkPath, 'Update', 'Hermes shortcut')) { return }
    if (-not (Test-Path -LiteralPath $BatPath)) { return }
    $w = New-Object -ComObject WScript.Shell
    $s = $w.CreateShortcut($LnkPath)
    if ($s.TargetPath -notmatch '\.bat$') { return }
    $s.TargetPath = Join-Path $env:SystemRoot 'System32\cmd.exe'
    $s.Arguments = '/c "' + $BatPath + '"'
    $s.WorkingDirectory = $RepoRoot
    if ($IconPath -and (Test-Path -LiteralPath $IconPath)) {
        $s.IconLocation = $IconPath + ',0'
    }
    $s.Save()
}

$whiteIco = Join-Path $scriptDir 'hermes_taskbar_white.ico'
Repair-HermesBatShortcut -LnkPath (Join-Path $scriptDir 'Hermes - setup Windows - naar taakbalk slepen.lnk') `
    -BatPath (Join-Path $scriptDir 'setup_hermes_windows.bat') -RepoRoot $RepoRoot -IconPath $whiteIco
$openBat = Join-Path $scriptDir 'OPEN_SETUP.bat'
if (Test-Path -LiteralPath $openBat) {
    Repair-HermesBatShortcut -LnkPath (Join-Path $scriptDir 'Hermes - Open Setup - naar taakbalk slepen.lnk') `
        -BatPath $openBat -RepoRoot $RepoRoot -IconPath $whiteIco
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

$pinnedDir = Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar'
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
    Write-Host '  [INFO] Geen map User Pinned\TaskBar - pin handmatig via rechtsklik.' -ForegroundColor Gray
}

# Icooncache verversen (oude H-stub of cmd-icoon verdwijnt soms pas na dit).
$ie4u = Join-Path $env:SystemRoot 'System32\ie4uinit.exe'
if (Test-Path -LiteralPath $ie4u) {
    Start-Process -FilePath $ie4u -ArgumentList '-show' -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
}

if (-not $Quiet) {
    Write-Host ''
    Write-Host 'Als het icoon nog het oude H toont:' -ForegroundColor Cyan
    Write-Host '  1. Pin losmaken (rechtsklik taakbalk -> Losmaken)' -ForegroundColor Gray
    Write-Host '  2. windows\Hermes - update - naar taakbalk slepen.lnk -> rechtsklik -> Vastmaken aan taakbalk' -ForegroundColor Gray
    Write-Host '  3. Of: dit script opnieuw draaien na REFRESH_TASKBAR_SHORTCUTS.bat' -ForegroundColor Gray
}

exit 0
