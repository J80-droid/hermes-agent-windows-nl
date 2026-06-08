# Gateway: .cmd vernieuwen + starten (geen UAC). Gebruik na login-install of bij "not running".
$ErrorActionPreference = 'Stop'

$windowsDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$repoRoot = (Resolve-Path (Join-Path $windowsDir '..')).Path
Set-Location -LiteralPath $repoRoot

. (Join-Path $windowsDir 'HermesPythonPolicy.ps1')
. (Join-Path $windowsDir 'scripts\GatewayWindowsCommon.ps1')

$py = Resolve-HermesPythonExe -RepoRoot $repoRoot -RequirePip
if (-not $py) {
    Write-Host 'ERROR: hermes-env niet gevonden. Draai windows\REPAIR_PYTHON.bat.' -ForegroundColor Red
    exit 1
}

$taskName = Set-HermesGatewayProfileFromScheduledTask
$probe = Join-Path $windowsDir 'scripts\gateway_pids_probe.py'
$refresh = Join-Path $windowsDir 'scripts\gateway_refresh_task_script.py'

Write-Host '=== Hermes gateway ensure running ===' -ForegroundColor Cyan
Write-Host "Scheduled Task: $taskName" -ForegroundColor DarkGray

& $py $refresh
if ($LASTEXITCODE -ne 0) {
    Write-Host '[FAIL] Task-script vernieuwen mislukt' -ForegroundColor Red
    exit 1
}
Write-Host ''

$pids = Get-HermesGatewayPids -Python $py -ProbeScript $probe
if ($pids.Count -gt 0) {
    Write-Host "[OK] Gateway draait al (PID: $($pids -join ', '))" -ForegroundColor Green
} else {
    Write-Host 'Gateway niet actief - start Scheduled Task...' -ForegroundColor Yellow
    schtasks /Run /TN $taskName 2>$null | Out-Null
    Start-Sleep -Seconds 8
    $pids = Get-HermesGatewayPids -Python $py -ProbeScript $probe
    if ($pids.Count -eq 0) {
        Write-Host 'Fallback: hermes gateway start...' -ForegroundColor Yellow
        'y' | & $py -m hermes_cli_entry gateway start 2>&1 | Out-Host
        Start-Sleep -Seconds 6
    }
}

Write-Host ''
Write-Host '=== Gateway status ===' -ForegroundColor Cyan
& $py -m hermes_cli_entry gateway status

$pids = Get-HermesGatewayPids -Python $py -ProbeScript $probe
if ($pids.Count -gt 0) {
    Write-Host ''
    Write-Host "[OK] Klaar. Autostart bij login via Scheduled Task $taskName." -ForegroundColor Green
    exit 0
}

Write-Host ''
Write-Host '[WARN] Geen gateway-proces. Run windows\GATEWAY_INSTALL_LOGIN.bat (UAC) of controleer logs onder %LOCALAPPDATA%\hermes\profiles\<profiel>\logs\' -ForegroundColor Yellow
exit 1
