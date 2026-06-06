# Hermes gateway: Scheduled Task / login autostart (+ start nu).
# Opent UAC zodat je op Ja/OK kunt klikken. Gebruikt hermes-env python (geen conda in PATH nodig).
$ErrorActionPreference = 'Stop'

$windowsDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$repoRoot = (Resolve-Path (Join-Path $windowsDir '..')).Path
Set-Location -LiteralPath $repoRoot

. (Join-Path $windowsDir 'HermesPythonPolicy.ps1')
. (Join-Path $windowsDir 'scripts\GatewayWindowsCommon.ps1')

$py = Resolve-HermesPythonExe -RepoRoot $repoRoot -RequirePip
if (-not $py) {
    Write-Host 'ERROR: hermes-env python.exe niet gevonden. Draai windows\REPAIR_PYTHON.bat.' -ForegroundColor Red
    Read-Host 'Druk Enter om te sluiten'
    exit 1
}

$taskName = Set-HermesGatewayProfileFromScheduledTask
$env:HERMES_GATEWAY_INSTALL_START_ON_LOGIN = '1'
$env:HERMES_GATEWAY_INSTALL_START_NOW = '1'

$elevPy = Join-Path $windowsDir 'scripts\gateway_install_login_elevated.py'
$probe = Join-Path $windowsDir 'scripts\gateway_pids_probe.py'
$refresh = Join-Path $windowsDir 'scripts\gateway_refresh_task_script.py'

Write-Host '=== Hermes gateway install (autostart bij login) ===' -ForegroundColor Cyan
if ($taskName -eq 'Hermes_Gateway') {
    Write-Host 'Er verschijnt een UAC-venster - klik op Ja/OK.' -ForegroundColor Yellow
} else {
    Write-Host "Task $taskName gevonden - UAC alleen nodig bij eerste install." -ForegroundColor DarkGray
}
Write-Host ''

$running = $false
$statusOut = (& $py -m hermes_cli.main gateway status 2>&1 | Out-String)
$taskInstalled = ($statusOut -match 'Scheduled Task registered')

if ($taskInstalled) {
    Write-Host 'Scheduled Task is al geinstalleerd - vernieuw task-script (geen UAC)...' -ForegroundColor DarkGray
    & $py $refresh
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[WARN] Task-script vernieuwen mislukt' -ForegroundColor Yellow
    } elseif (Test-HermesGatewayRunning -Python $py -ProbeScript $probe) {
        $running = $true
    }
}

if (-not $taskInstalled) {
    & $py $elevPy
    if ($LASTEXITCODE -eq 0) {
        Write-Host ''
        Write-Host 'Wacht tot de elevated install klaar is (max 90s)...' -ForegroundColor DarkGray
        $deadline = (Get-Date).AddSeconds(90)
        while ((Get-Date) -lt $deadline) {
            if (Test-HermesGatewayRunning -Python $py -ProbeScript $probe) {
                $running = $true
                break
            }
            Start-Sleep -Seconds 2
        }
    } else {
        Write-Host ''
        Write-Host 'Fallback: gateway install in dit venster (beantwoord y op UAC-vraag)...' -ForegroundColor Yellow
        'y' | & $py -m hermes_cli.main gateway install --start-on-login --start-now
    }
}

if (-not $running) {
    Write-Host ''
    Write-Host 'Gateway nog niet actief - probeer schtasks /Run...' -ForegroundColor Yellow
    schtasks /Run /TN $taskName 2>$null | Out-Null
    Start-Sleep -Seconds 6
    if (-not (Test-HermesGatewayRunning -Python $py -ProbeScript $probe)) {
        Write-Host 'Fallback: hermes gateway start...' -ForegroundColor Yellow
        'y' | & $py -m hermes_cli.main gateway start
        Start-Sleep -Seconds 6
    }
}

Write-Host ''
Write-Host '=== Gateway status ===' -ForegroundColor Cyan
& $py -m hermes_cli.main gateway status

if (Test-HermesGatewayRunning -Python $py -ProbeScript $probe) {
    Write-Host ''
    Write-Host "[OK] Gateway actief + login-autostart ($taskName)." -ForegroundColor Green
    Write-Host '     Last Run Result 1 bij Scheduled Task is vaak normaal (pythonw start op achtergrond).' -ForegroundColor DarkGray
} else {
    Write-Host ''
    Write-Host '[TIP] Zonder UAC: windows\GATEWAY_ENSURE_RUNNING.bat' -ForegroundColor Yellow
}

Write-Host ''
Read-Host 'Druk Enter om dit venster te sluiten'
