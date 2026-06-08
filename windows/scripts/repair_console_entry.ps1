<#
.SYNOPSIS
    Align ``hermes`` console-script op ``hermes_cli_entry`` en vernieuw gateway.cmd.
.DESCRIPTION
    0. ``repair_terminal_cwd.ps1`` — migreer legacy TERMINAL_CWD uit profiel-.env naar config.yaml
    1. ``pip install -e .`` in repo-root (editable shim)
    2. ``gateway_refresh_task_script.py`` (overlay + hermes_cli_entry in gateway.cmd)
    3. Optioneel Scheduled Task /Run als gateway nog niet draait
#>
param(
    [switch]$SkipGateway,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$windowsDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$repoRoot = (Resolve-Path (Join-Path $windowsDir '..\..')).Path
Set-Location -LiteralPath $repoRoot

. (Join-Path (Join-Path $repoRoot 'windows') 'HermesPythonPolicy.ps1')
. (Join-Path $windowsDir 'GatewayWindowsCommon.ps1')
. (Join-Path $windowsDir 'HermesHomeCommon.ps1')

function Write-RepairLine {
    param([string]$Message, [string]$Level = 'INFO')
    if ($Quiet) { return }
    switch ($Level) {
        'OK' { Write-Host $Message -ForegroundColor Green }
        'WARN' { Write-Host $Message -ForegroundColor Yellow }
        'ERROR' { Write-Host $Message -ForegroundColor Red }
        default { Write-Host $Message -ForegroundColor Cyan }
    }
}

Initialize-UserHermesHomeRoot -FixUserEnv -Quiet | Out-Null

$terminalCwdRepair = Join-Path $windowsDir 'repair_terminal_cwd.ps1'
if (Test-Path -LiteralPath $terminalCwdRepair) {
    Write-RepairLine 'TERMINAL_CWD migratie (.env -> config.yaml terminal.cwd)...'
    & $terminalCwdRepair -RepoRoot $repoRoot -Quiet
}

$py = Resolve-HermesPythonExe -RepoRoot $repoRoot -RequirePip
if (-not $py -or -not (Test-Path -LiteralPath $py)) {
    Write-RepairLine 'hermes-env python niet gevonden. Draai windows\REPAIR_PYTHON.bat.' ERROR
    exit 1
}

Write-RepairLine "Python: $py"
Write-RepairLine 'pip install -e . (console-script hermes -> hermes_cli_entry)...'
& $py -m pip install -e $repoRoot
if ($LASTEXITCODE -ne 0) {
    Write-RepairLine "pip install -e mislukt (exit $LASTEXITCODE)" ERROR
    exit $LASTEXITCODE
}

$entryCheck = & $py -c @"
from importlib.metadata import entry_points
eps = [e for e in entry_points(group='console_scripts') if e.name == 'hermes']
print(eps[0].value if eps else '')
"@
if ($entryCheck -ne 'hermes_cli_entry:main') {
    Write-RepairLine "WARN: hermes entry point is '$entryCheck' (verwacht hermes_cli_entry:main)" WARN
} else {
    Write-RepairLine '[OK] Console-script hermes -> hermes_cli_entry:main' OK
}

if ($SkipGateway) {
    Write-RepairLine 'Gateway-stap overgeslagen (-SkipGateway).' WARN
    exit 0
}

$refresh = Join-Path $windowsDir 'gateway_refresh_task_script.py'
if (-not (Test-Path -LiteralPath $refresh)) {
    Write-RepairLine "gateway_refresh_task_script.py ontbreekt: $refresh" ERROR
    exit 1
}

Write-RepairLine 'Gateway.cmd vernieuwen (overlay + hermes_cli_entry)...'
& $py $refresh
if ($LASTEXITCODE -ne 0) {
    Write-RepairLine 'gateway.cmd refresh mislukt' ERROR
    exit $LASTEXITCODE
}

$taskName = Set-HermesGatewayProfileFromScheduledTask
$probe = Join-Path $windowsDir 'gateway_pids_probe.py'
$taskInstalled = $false
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $statusOut = (& $py -m hermes_cli_entry gateway status 2>&1 | Out-String)
} finally {
    $ErrorActionPreference = $prevEap
}
if ($statusOut -match 'Scheduled Task registered') {
    $taskInstalled = $true
}

if (-not $taskInstalled) {
    Write-RepairLine 'Geen Scheduled Task - installeer via windows\GATEWAY_INSTALL_LOGIN.ps1 of:' WARN
    Write-RepairLine '  hermes gateway install --start-on-login --start-now' WARN
    exit 0
}

if (Test-HermesGatewayRunning -Python $py -ProbeScript $probe) {
    Write-RepairLine "[OK] Gateway actief ($taskName); gateway.cmd vernieuwd." OK
    exit 0
}

Write-RepairLine "Gateway nog niet actief - schtasks /Run $taskName ..."
schtasks /Run /TN $taskName 2>$null | Out-Null
Start-Sleep -Seconds 6
if (Test-HermesGatewayRunning -Python $py -ProbeScript $probe) {
    Write-RepairLine '[OK] Gateway gestart na task refresh.' OK
    exit 0
}

Write-RepairLine 'Gateway start niet automatisch - probeer: hermes gateway start' WARN
exit 0
