# Start Hermes web dashboard (127.0.0.1:9119) zonder browser-tab.
#
# Env:
#   HERMES_SKIP_DASHBOARD_ON_START=1  - niet starten
#   HERMES_DASHBOARD_ON_START=0       - niet starten
#   HERMES_DASHBOARD_PORT             - default 9119 (1-65535)
#   HERMES_DASHBOARD_HOST             - default 127.0.0.1
#   HERMES_DASHBOARD_SKIP_BUILD=1     - geef --skip-build door aan hermes dashboard
#   HERMES_LAUNCH_LOG                 - optioneel: append statusregels (ook bij -Quiet)
#
# Tests: pytest tests/windows/test_launch_dashboard_on_start.py
# E2E:    audits/RUN_DASHBOARD_ON_START_E2E.bat

param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

function Write-LaunchLogAppend {
    param([string]$Line)
    $logPath = $env:HERMES_LAUNCH_LOG
    if (-not $logPath) { return }
    try {
        $dir = Split-Path -Parent $logPath
        if ($dir -and -not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        Add-Content -LiteralPath $logPath -Value $Line -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch { }
}

function Write-DashLog {
    param([string]$Message, [string]$Color = 'Cyan')
    Write-LaunchLogAppend $Message
    if ($Quiet) { return }
    Write-Host $Message -ForegroundColor $Color
}

if ($env:HERMES_SKIP_DASHBOARD_ON_START -eq '1') {
    Write-DashLog '[INFO] Dashboard overgeslagen (HERMES_SKIP_DASHBOARD_ON_START=1).' -Color DarkGray
    exit 0
}
if ($env:HERMES_DASHBOARD_ON_START -eq '0') {
    Write-DashLog '[INFO] Dashboard overgeslagen (HERMES_DASHBOARD_ON_START=0).' -Color DarkGray
    exit 0
}

if (-not $RepoRoot -and $env:HERMES_REPO_ROOT) {
    $RepoRoot = $env:HERMES_REPO_ROOT.Trim().Trim('"')
}
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$port = 9119
if ($env:HERMES_DASHBOARD_PORT -match '^\d+$') {
    $port = [int]$env:HERMES_DASHBOARD_PORT
}
if ($port -lt 1 -or $port -gt 65535) {
    Write-DashLog "[WARN] Ongeldige HERMES_DASHBOARD_PORT=$port - gebruik 9119." -Color Yellow
    $port = 9119
}

$hostAddr = if ($env:HERMES_DASHBOARD_HOST) { $env:HERMES_DASHBOARD_HOST.Trim() } else { '127.0.0.1' }

$condaPaths = @(
    (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
    (Join-Path $env:ProgramData 'miniconda3\Scripts\conda.exe'),
    (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe'),
    (Join-Path $env:ProgramData 'anaconda3\Scripts\conda.exe')
)
$condaExe = $condaPaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $condaExe) {
    Write-DashLog '[WARN] Dashboard niet gestart: conda.exe niet gevonden.' -Color Yellow
    exit 0
}

function Get-DashboardConnectHost {
    param([string]$BindHost)
    switch -Regex ($BindHost) {
        '^localhost$' { return '127.0.0.1' }
        '^::1$' { return '::1' }
        default { return $BindHost }
    }
}

function Test-DashboardPortInUse {
    param([string]$BindHost, [int]$BindPort)
    $checkHost = Get-DashboardConnectHost -BindHost $BindHost
    $client = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($checkHost, $BindPort, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(800, $false)
        if ($ok -and $client.Connected) {
            return $true
        }
    } catch { }
    finally {
        if ($null -ne $client) {
            try { $client.Close() } catch { }
        }
    }
    return $false
}

if (Test-DashboardPortInUse -BindHost $hostAddr -BindPort $port) {
    Write-DashLog ("[OK] Dashboard al bereikbaar op http://${hostAddr}:${port}/sessions") -Color Green
    exit 0
}

$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $statusOut = & $condaExe run -n hermes-env --no-capture-output python -m hermes_cli.main dashboard --status 2>&1 | Out-String
    if ($statusOut -match 'dashboard process\(es\) running') {
        Write-DashLog ("[OK] Dashboard-proces al actief - open http://${hostAddr}:${port}/sessions") -Color Green
        exit 0
    }
} catch {
    Write-DashLog '[WARN] dashboard --status mislukt - probeer toch te starten.' -Color Yellow
} finally {
    $ErrorActionPreference = $prevEap
}

$logDir = Join-Path $RepoRoot 'output\research\logs'
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$dashLog = Join-Path $logDir 'hermes_dashboard.log'
$errLog = "${dashLog}.err"

$argList = @(
    'run', '-n', 'hermes-env', '--no-capture-output',
    'python', '-m', 'hermes_cli.main', 'dashboard',
    '--no-open', '--host', $hostAddr, '--port', "$port"
)
if ($env:HERMES_DASHBOARD_SKIP_BUILD -eq '1') {
    $argList += '--skip-build'
}

Write-DashLog "[INFO] Dashboard starten (geen browser): http://${hostAddr}:${port}/sessions" -Color Cyan
Write-DashLog ("[INFO] Log: $dashLog") -Color DarkGray

try {
    $proc = Start-Process -FilePath $condaExe `
        -ArgumentList $argList `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Minimized `
        -PassThru `
        -RedirectStandardOutput $dashLog `
        -RedirectStandardError $errLog
} catch {
    Write-DashLog ("[WARN] Start-Process dashboard mislukt: $($_.Exception.Message)") -Color Yellow
    exit 0
}

Start-Sleep -Seconds 3
if ($proc.HasExited -and $proc.ExitCode -ne 0) {
    Write-DashLog ("[WARN] Dashboard stopte vroeg (exit $($proc.ExitCode)). Zie $dashLog en $errLog") -Color Yellow
    exit 0
}
if (Test-DashboardPortInUse -BindHost $hostAddr -BindPort $port) {
    Write-DashLog '[OK] Dashboard op de achtergrond - open zelf een tab op /sessions' -Color Green
    exit 0
}
if (-not $proc.HasExited) {
    Write-DashLog '[OK] Dashboard start (build kan even duren) - controleer /sessions over ~30s' -Color Green
    exit 0
}
Write-DashLog ("[WARN] Poort ${port} nog niet bereikbaar. Zie $dashLog") -Color Yellow
exit 0
