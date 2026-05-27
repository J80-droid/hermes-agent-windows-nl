# Start Hermes web dashboard (127.0.0.1:9119). Browser-tab optioneel.
#
# Env:
#   HERMES_SKIP_DASHBOARD_ON_START=1  - niet starten
#   HERMES_DASHBOARD_ON_START=0       - niet starten
#   HERMES_DASHBOARD_PORT             - default 9119 (1-65535)
#   HERMES_DASHBOARD_HOST             - default 127.0.0.1
#   HERMES_DASHBOARD_SKIP_BUILD=1     - geef --skip-build door aan hermes dashboard
#   HERMES_DASHBOARD_OPEN_PATH        - bv. /codebase-viz (browser openen na start)
#   HERMES_SKIP_DASHBOARD_BROWSER=1   - geen browser openen
#   HERMES_LAUNCH_LOG                 - optioneel: append statusregels (ook bij -Quiet)
# Workspace plugins/codebase-viz: zet HERMES_BUNDLED_PLUGINS + pip install -e .[web]
#
# Tests: pytest tests/windows/test_launch_dashboard_on_start.py
# E2E:    audits/RUN_DASHBOARD_ON_START_E2E.bat

param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
Import-HermesPythonPolicy

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

function Get-DashboardConnectHost {
    param([string]$BindHost)
    switch -Regex ($BindHost) {
        '^localhost$' { return '127.0.0.1' }
        '^::1$' { return '::1' }
        default { return $BindHost }
    }
}

function Open-DashboardBrowserIfRequested {
    param(
        [string]$BindHost,
        [int]$BindPort
    )
    if ($env:HERMES_SKIP_DASHBOARD_BROWSER -eq '1') { return }
    $path = if ($env:HERMES_DASHBOARD_OPEN_PATH) { $env:HERMES_DASHBOARD_OPEN_PATH.Trim() } else { '' }
    if (-not $path) { return }
    if (-not $path.StartsWith('/')) { $path = "/$path" }
    $connectHost = Get-DashboardConnectHost -BindHost $BindHost
    $url = "http://${connectHost}:${BindPort}${path}"
    Write-DashLog "[INFO] Browser: $url" -Color Cyan
    try {
        Start-Process $url | Out-Null
    } catch {
        Write-DashLog "[WARN] Browser openen mislukt: $($_.Exception.Message)" -Color Yellow
    }
}

function Move-AsideStaleCodebaseVizUserPlugin {
    param([string]$Label, [string]$PluginDir)
    $api = Join-Path $PluginDir 'dashboard\plugin_api.py'
    if (-not (Test-Path -LiteralPath $api)) { return }
    $suffix = [Guid]::NewGuid().ToString('N').Substring(0, 8)
    $bakName = "codebase-viz.bak.$suffix"
    Write-DashLog "[INFO] Oude user-plugin ($Label) -> $bakName" -Color Yellow
    try {
        Rename-Item -LiteralPath $PluginDir -NewName $bakName -ErrorAction Stop
    } catch {
        Write-DashLog "[WARN] Kon $PluginDir niet hernoemen: $($_.Exception.Message)" -Color Yellow
    }
}

function Initialize-WorkspaceDashboardPlugins {
    param([string]$RepoRoot)
    $pluginsRoot = Join-Path $RepoRoot 'plugins'
    $manifest = Join-Path $pluginsRoot 'codebase-viz\dashboard\manifest.json'
    if (-not (Test-Path -LiteralPath $manifest)) { return }

    $env:HERMES_BUNDLED_PLUGINS = $pluginsRoot
    Write-DashLog "[INFO] HERMES_BUNDLED_PLUGINS=$pluginsRoot" -Color DarkGray
    if (-not $env:CODEBASE_VIZ_PYGOUNT_TIMEOUT) {
        $env:CODEBASE_VIZ_PYGOUNT_TIMEOUT = '240'
    }

    Move-AsideStaleCodebaseVizUserPlugin -Label 'profile' -PluginDir (Join-Path $env:USERPROFILE '.hermes\plugins\codebase-viz')
    if ($env:LOCALAPPDATA) {
        Move-AsideStaleCodebaseVizUserPlugin -Label 'localappdata' -PluginDir (Join-Path $env:LOCALAPPDATA 'hermes\plugins\codebase-viz')
    }
}

function New-CondaDashboardRunArgs {
    param([string[]]$PythonArgs)
    # Geen ``conda run -e`` — veel Windows-conda builds ondersteunen dat niet.
    # Zet HERMES_BUNDLED_PLUGINS / CODEBASE_VIZ_PYGOUNT_TIMEOUT op $env: vóór aanroep;
    # ``conda run`` erft de shell-omgeving.
    $runArgs = @('run', '-n', 'hermes-env', '--no-capture-output', 'python', '-m', 'hermes_cli.main')
    $runArgs += $PythonArgs
    return $runArgs
}

function Get-DashboardPythonExe {
    param([string]$RepoRoot)
    if (-not (Import-HermesPythonPolicy)) {
        if ($env:HERMES_PYTHON -and (Test-Path -LiteralPath $env:HERMES_PYTHON)) {
            return $env:HERMES_PYTHON
        }
    } elseif (Get-Command Resolve-HermesPythonExe -ErrorAction SilentlyContinue) {
        $py = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
        if ($py) { return $py }
    }
    if ($env:HERMES_PYTHON -and (Test-Path -LiteralPath $env:HERMES_PYTHON)) {
        return $env:HERMES_PYTHON
    }
    $fallback = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if (Test-Path -LiteralPath $fallback) { return $fallback }
    return $null
}

function New-HermesDashboardCliArgs {
    param([string[]]$PythonArgs)
    $cli = @('-m', 'hermes_cli.main')
    $cli += $PythonArgs
    return $cli
}

function Stop-HermesDashboardProcess {
    param([string]$CondaExe)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $stopArgs = New-CondaDashboardRunArgs -PythonArgs @('dashboard', '--stop')
    try {
        $null = & $CondaExe @stopArgs 2>&1
    } catch { }
    $py = Get-DashboardPythonExe -RepoRoot $RepoRoot
    if ($py) {
        try {
            $null = & $py -m hermes_cli.main dashboard --stop 2>&1
        } catch { }
    }
    try {
        $null = & $CondaExe run -n hermes-env --no-capture-output python -m hermes_cli.main dashboard --stop 2>&1
    } catch { }
    $ErrorActionPreference = $prevEap
    Start-Sleep -Seconds 3
}

function Install-HermesWebDashboardPackage {
    param(
        [string]$RepoRoot,
        [string]$CondaExe
    )
    $editable = "${RepoRoot}[web]"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $py = Get-DashboardPythonExe -RepoRoot $RepoRoot
    try {
        if ($py) {
            $null = & $py -m pip install -e $editable -q 2>&1
            if ($env:HERMES_BUNDLED_PLUGINS) {
                $null = & $py -m pip install pygount -q 2>&1
            }
        } elseif ($CondaExe) {
            $null = & $CondaExe run -n hermes-env --no-capture-output python -m pip install -e $editable -q 2>&1
            if ($env:HERMES_BUNDLED_PLUGINS) {
                $null = & $CondaExe run -n hermes-env --no-capture-output python -m pip install pygount -q 2>&1
            }
        } else {
            Write-DashLog '[WARN] Geen Python voor pip install -e [web].' -Color Yellow
            return
        }
        Write-DashLog '[INFO] Dashboard-deps bijgewerkt (editable + web + pygount).' -Color DarkGray
    } catch {
        Write-DashLog "[WARN] pip install -e [web] mislukt: $($_.Exception.Message)" -Color Yellow
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Test-CodebaseVizHealth {
    param(
        [string]$RepoRoot,
        [string]$PythonExe,
        [string]$BindHost,
        [int]$BindPort,
        [int]$MaxWaitSec = 40
    )
    if (-not $env:HERMES_BUNDLED_PLUGINS) { return $true }
    $connectHost = Get-DashboardConnectHost -BindHost $BindHost
    $url = "http://${connectHost}:${BindPort}/codebase-viz"
    $deadline = (Get-Date).AddSeconds($MaxWaitSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-DashboardPortInUse -BindHost $BindHost -BindPort $BindPort) {
            try {
                $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
                if ($r.StatusCode -eq 200) { break }
            } catch { }
        }
        Start-Sleep -Seconds 2
    }
    if (-not (Test-DashboardPortInUse -BindHost $BindHost -BindPort $BindPort)) {
        Write-DashLog '[WARN] Codebase Viz health: dashboard-poort niet bereikbaar.' -Color Yellow
        return $false
    }
    $verify = Join-Path $RepoRoot 'audits\verify_codebase_viz_health.py'
    if (-not (Test-Path -LiteralPath $verify)) {
        Write-DashLog '[WARN] Codebase Viz health: verify-script ontbreekt.' -Color Yellow
        return $false
    }
    $hadTimeout = $null -ne $env:CODEBASE_VIZ_PYGOUNT_TIMEOUT
    $prevTimeout = $env:CODEBASE_VIZ_PYGOUNT_TIMEOUT
    if (-not $hadTimeout) { $env:CODEBASE_VIZ_PYGOUNT_TIMEOUT = '240' }
    try {
        & $PythonExe $verify 2>&1 | ForEach-Object { Write-LaunchLogAppend $_ }
        if ($LASTEXITCODE -eq 0) {
            Write-DashLog '[OK] Codebase Viz /health verify geslaagd.' -Color Green
            return $true
        }
        Write-DashLog '[WARN] Codebase Viz /health verify mislukt (exit ' + $LASTEXITCODE + '). Zie audits\RESTART_CODEBASE_VIZ_DASHBOARD.bat' -Color Yellow
        return $false
    } catch {
        Write-DashLog "[WARN] Codebase Viz verify: $($_.Exception.Message)" -Color Yellow
        return $false
    } finally {
        if ($hadTimeout) {
            $env:CODEBASE_VIZ_PYGOUNT_TIMEOUT = $prevTimeout
        } else {
            Remove-Item Env:CODEBASE_VIZ_PYGOUNT_TIMEOUT -ErrorAction SilentlyContinue
        }
    }
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

Initialize-WorkspaceDashboardPlugins -RepoRoot $RepoRoot

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

$workspacePlugins = [bool]$env:HERMES_BUNDLED_PLUGINS

if ($workspacePlugins) {
    Write-DashLog '[INFO] Workspace plugins: dashboard herstarten (voorkomt oude 30s pygount-cache).' -Color DarkGray
    Stop-HermesDashboardProcess -CondaExe $condaExe
} else {
    if (Test-DashboardPortInUse -BindHost $hostAddr -BindPort $port) {
        Write-DashLog ("[OK] Dashboard al bereikbaar op http://${hostAddr}:${port}/sessions") -Color Green
        Open-DashboardBrowserIfRequested -BindHost $hostAddr -BindPort $port
        exit 0
    }

    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $statusArgs = New-CondaDashboardRunArgs -PythonArgs @('dashboard', '--status')
        $statusOut = & $condaExe @statusArgs 2>&1 | Out-String
        if ($statusOut -match 'dashboard process\(es\) running') {
            Write-DashLog ("[OK] Dashboard-proces al actief - open http://${hostAddr}:${port}/sessions") -Color Green
            Open-DashboardBrowserIfRequested -BindHost $hostAddr -BindPort $port
            exit 0
        }
    } catch {
        Write-DashLog '[WARN] dashboard --status mislukt - probeer toch te starten.' -Color Yellow
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

Install-HermesWebDashboardPackage -RepoRoot $RepoRoot -CondaExe $condaExe

$logDir = Join-Path $RepoRoot 'output\research\logs'
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$dashLog = Join-Path $logDir 'hermes_dashboard.log'
$errLog = "${dashLog}.err"

$dashPythonArgs = @(
    'dashboard', '--no-open', '--host', $hostAddr, '--port', "$port"
)
if ($env:HERMES_DASHBOARD_SKIP_BUILD -eq '1') {
    $dashPythonArgs += '--skip-build'
}
$dashPy = Get-DashboardPythonExe -RepoRoot $RepoRoot
if (-not $dashPy) {
    Write-DashLog '[WARN] Dashboard niet gestart: geen hermes-env python.exe.' -Color Yellow
    exit 0
}
$argList = New-HermesDashboardCliArgs -PythonArgs $dashPythonArgs

Write-DashLog "[INFO] Dashboard starten (geen browser): http://${hostAddr}:${port}/sessions" -Color Cyan
Write-DashLog ("[INFO] Python: $dashPy") -Color DarkGray
Write-DashLog ("[INFO] Log: $dashLog") -Color DarkGray

try {
    $proc = Start-Process -FilePath $dashPy `
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
    Write-DashLog '[OK] Dashboard op de achtergrond.' -Color Green
    $null = Test-CodebaseVizHealth -RepoRoot $RepoRoot -PythonExe $dashPy -BindHost $hostAddr -BindPort $port
    Open-DashboardBrowserIfRequested -BindHost $hostAddr -BindPort $port
    exit 0
}
if (-not $proc.HasExited) {
    Write-DashLog '[OK] Dashboard start (build kan even duren).' -Color Green
    $null = Test-CodebaseVizHealth -RepoRoot $RepoRoot -PythonExe $dashPy -BindHost $hostAddr -BindPort $port
    Open-DashboardBrowserIfRequested -BindHost $hostAddr -BindPort $port
    exit 0
}
Write-DashLog ("[WARN] Poort ${port} nog niet bereikbaar. Zie $dashLog") -Color Yellow
exit 0
