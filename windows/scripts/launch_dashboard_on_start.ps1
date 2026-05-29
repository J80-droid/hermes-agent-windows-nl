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
#   HERMES_DASHBOARD_QUICK_START=1    - geen /health-wacht bij interactieve launch (orchestrator zet dit)
#   HERMES_DASHBOARD_WINDOW_STYLE      - hidden (default) | minimized | normal
#   HERMES_LAUNCH_LOG                 - optioneel: append statusregels (ook bij -Quiet)
#   HERMES_CODEBASE_VIZ_SKIP_BUILD=1  - geen npm run build bij verouderde src
#   HERMES_CODEBASE_VIZ_PREGOUNT_CACHE - skip|0 = geen pygount pre-warm bij start
#   HERMES_CODEBASE_VIZ_WARMUP        - auto (default): force-scan na health | incremental | 0/skip
#   HERMES_FORCE_DASHBOARD_PIP=1      - forceer pip install -e .[web] (normaal: manifest in %LOCALAPPDATA%\hermes\web-dashboard-deps.json)
# Workspace plugins/codebase-viz: HERMES_BUNDLED_PLUGINS; pip alleen bij gewijzigde pyproject/package.json.
# Ongeldige pygount-cache (bijv. pytest-temp): auto-verwijderd; handmatig: windows\FIX_CODEBASE_VIZ_CACHE.bat
#
# Tests: pytest tests/windows/test_launch_dashboard_on_start.py
# E2E:    audits/RUN_DASHBOARD_ON_START_E2E.bat

param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$script:DashQuiet = [bool]$Quiet.IsPresent
[void][bool]$Quiet
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
    } catch {
        $null = $_.Exception.Message
    }
}

function Write-DashLog {
    param([string]$Message, [string]$Color = 'Cyan')
    Add-HermesLaunchLogLine -Message $Message
    if ($script:DashQuiet) { return }
    $level = 'Info'
    if ($Color -eq 'Yellow') { $level = 'Warn' }
    elseif ($Color -eq 'Green') { $level = 'Ok' }
    elseif ($Color -eq 'Red') { $level = 'Error' }
    elseif ($Color -eq 'DarkGray' -or $Color -eq 'Gray') { $level = 'Detail' }
    [void](Write-HermesLaunchUi -Message $Message -Level $level)
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
    if (-not (Test-Path -LiteralPath $manifest)) {
        return [pscustomobject]@{ BundledPlugins = $false; DistRebuilt = $false }
    }

    $env:HERMES_BUNDLED_PLUGINS = $pluginsRoot
    Write-DashLog "[INFO] HERMES_BUNDLED_PLUGINS=$pluginsRoot" -Color DarkGray
    if (-not $env:CODEBASE_VIZ_PYGOUNT_TIMEOUT) {
        $env:CODEBASE_VIZ_PYGOUNT_TIMEOUT = '240'
    }
    if (-not $env:CODEBASE_VIZ_TTL) {
        $env:CODEBASE_VIZ_TTL = '300'
    }
    if (-not $env:CODEBASE_VIZ_PYGOUNT_TTL) {
        $env:CODEBASE_VIZ_PYGOUNT_TTL = '3600'
    }

    Move-AsideStaleCodebaseVizUserPlugin -Label 'profile' -PluginDir (Join-Path $env:USERPROFILE '.hermes\plugins\codebase-viz')
    if ($env:LOCALAPPDATA) {
        Move-AsideStaleCodebaseVizUserPlugin -Label 'localappdata' -PluginDir (Join-Path $env:LOCALAPPDATA 'hermes\plugins\codebase-viz')
    }
    $distRebuilt = Update-CodebaseVizDistIfNeeded -RepoRoot $RepoRoot
    return [pscustomobject]@{ BundledPlugins = $true; DistRebuilt = [bool]$distRebuilt }
}

function Update-CodebaseVizDistIfNeeded {
    [CmdletBinding(SupportsShouldProcess)]
    param([string]$RepoRoot)
    if ($env:HERMES_CODEBASE_VIZ_SKIP_BUILD -eq '1') { return $false }
    $dashDir = Join-Path $RepoRoot 'plugins\codebase-viz\dashboard'
    $pkg = Join-Path $dashDir 'package.json'
    if (-not (Test-Path -LiteralPath $pkg)) { return $false }

    $dist = Join-Path $dashDir 'dist\index.js'
    $needsBuild = -not (Test-Path -LiteralPath $dist)
    if (-not $needsBuild) {
        $distTime = (Get-Item -LiteralPath $dist).LastWriteTimeUtc
        $srcDir = Join-Path $dashDir 'src'
        if (Test-Path -LiteralPath $srcDir) {
            $newest = Get-ChildItem -LiteralPath $srcDir -Recurse -File -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTimeUtc -Descending |
                Select-Object -First 1
            if ($newest -and $newest.LastWriteTimeUtc -gt $distTime) {
                $needsBuild = $true
            }
        }
    }
    if (-not $needsBuild) { return $false }
    if (-not $PSCmdlet.ShouldProcess($dashDir, 'Build Codebase Viz dist')) { return $false }

    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Write-DashLog '[WARN] Codebase Viz: dist verouderd maar npm niet op PATH.' -Color Yellow
        return $false
    }
    Update-HermesLaunchActivity -Reason 'Codebase Viz: npm run build (kan enkele minuten)...'
    Write-DashLog '[INFO] Codebase Viz: npm run build (src nieuwer dan dist)...' -Color Cyan
    $built = $false
    Push-Location -LiteralPath $dashDir
    try {
        if ((Get-Command Test-HermesLaunchConsoleCapture -ErrorAction SilentlyContinue) -and (Test-HermesLaunchConsoleCapture)) {
            $npmCode = Invoke-HermesCapturedProcess -FilePath 'npm.cmd' -ArgumentList @('run', 'build') -WorkingDirectory $dashDir -Quiet -FilterNoise
            if ($npmCode -ne 0) {
                Write-DashLog '[WARN] Codebase Viz npm run build mislukt.' -Color Yellow
            } else {
                Write-DashLog '[OK] Codebase Viz dist gebouwd.' -Color Green
                $built = $true
            }
        } else {
            & npm run build 2>&1 | ForEach-Object { Write-LaunchLogAppend "$_" }
            if ($LASTEXITCODE -ne 0) {
                Write-DashLog '[WARN] Codebase Viz npm run build mislukt.' -Color Yellow
            } else {
                Write-DashLog '[OK] Codebase Viz dist gebouwd.' -Color Green
                $built = $true
            }
        }
    } catch {
        Write-DashLog "[WARN] Codebase Viz build: $($_.Exception.Message)" -Color Yellow
    } finally {
        Pop-Location
    }
    return $built
}

function Get-CondaDashboardRunArgs {
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

function Get-HermesDashboardCliArgs {
    param([string[]]$PythonArgs)
    $cli = @('-m', 'hermes_cli.main')
    $cli += $PythonArgs
    return $cli
}

function Stop-HermesDashboardProcess {
    [CmdletBinding(SupportsShouldProcess)]
    param([string]$CondaExe)
    if (-not $PSCmdlet.ShouldProcess('Hermes dashboard', 'Stop')) { return }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $stopArgs = Get-CondaDashboardRunArgs -PythonArgs @('dashboard', '--stop')
    try {
        $null = & $CondaExe @stopArgs 2>&1
    } catch {
        $null = $_.Exception.Message
    }
    $py = Get-DashboardPythonExe -RepoRoot $RepoRoot
    if ($py) {
        try {
            $null = & $py -m hermes_cli.main dashboard --stop 2>&1
        } catch {
            $null = $_.Exception.Message
        }
    }
    if ($CondaExe) {
        try {
            $stopArgs = Get-CondaDashboardRunArgs -PythonArgs @('dashboard', '--stop')
            $null = & $CondaExe @stopArgs 2>&1
        } catch {
            $null = $_.Exception.Message
        }
    }
    $ErrorActionPreference = $prevEap
    Start-Sleep -Seconds 3
}

function Install-HermesWebDashboardPackage {
    param(
        [string]$RepoRoot
    )
    $requirePygount = [bool]$env:HERMES_BUNDLED_PLUGINS
    if (-not (Test-HermesNeedsWebDashboardPipInstall -RepoRoot $RepoRoot -RequirePygount:$requirePygount)) {
        Write-DashLog '[OK] Dashboard-deps up-to-date (web manifest).' -Color DarkGray
        return $false
    }
    $editable = "${RepoRoot}[web]"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $py = Get-DashboardPythonExe -RepoRoot $RepoRoot
    $changed = $false
    try {
        if ($py) {
            Update-HermesLaunchActivity -Reason 'Dashboard: pip install -e [web]...'
            $null = & $py -m pip install -e $editable -q 2>&1
            if ($requirePygount) {
                $null = & $py -m pip install pygount -q 2>&1
            }
            if ($LASTEXITCODE -eq 0) {
                [void](Write-HermesWebDashboardDepsManifest -RepoRoot $RepoRoot -PythonExe $py -RequirePygount:$requirePygount)
                $changed = $true
            }
        } else {
            Write-DashLog '[WARN] Geen Python voor pip install -e [web].' -Color Yellow
            return $false
        }
        Write-DashLog '[INFO] Dashboard-deps bijgewerkt (editable + web + pygount).' -Color DarkGray
    } catch {
        Write-DashLog "[WARN] pip install -e [web] mislukt: $($_.Exception.Message)" -Color Yellow
    } finally {
        $ErrorActionPreference = $prevEap
    }
    return $changed
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
            } catch {
                $null = $_.Exception.Message
            }
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
            Invoke-CodebaseVizWarmupScan -BindHost $BindHost -BindPort $BindPort -RepoRoot $RepoRoot -PythonExe $PythonExe
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

function Ensure-CodebaseVizPygountCache {
    param(
        [string]$RepoRoot,
        [string]$PythonExe
    )
    if (-not $env:HERMES_BUNDLED_PLUGINS) { return }
    if (-not $PythonExe) { return }
    $pregount = ''
    if ($null -ne $env:HERMES_CODEBASE_VIZ_PREGOUNT_CACHE) {
        $pregount = "$env:HERMES_CODEBASE_VIZ_PREGOUNT_CACHE".Trim().ToLowerInvariant()
    }
    if ($pregount -in @('0', 'skip', 'off', 'false', 'no')) {
        Write-DashLog '[INFO] Codebase Viz pre-warm overgeslagen (HERMES_CODEBASE_VIZ_PREGOUNT_CACHE).' -Color DarkGray
        return
    }
    $warmScript = Join-Path $RepoRoot 'scripts\warm_codebase_viz_pygount_cache.py'
    if (-not (Test-Path -LiteralPath $warmScript)) {
        Write-DashLog '[WARN] Codebase Viz pre-warm: script ontbreekt.' -Color Yellow
        return
    }
    if (-not $env:CODEBASE_VIZ_REPO) {
        $env:CODEBASE_VIZ_REPO = $RepoRoot
    }
    if (Test-HermesCodebaseVizPygountCacheMismatch -RepoRoot $RepoRoot) {
        [void](Clear-HermesCodebaseVizPygountCache -RepoRoot $RepoRoot -Reason 'ongeldig repo-pad (bijv. pytest)')
    }
    $checkCode = Invoke-HermesCodebaseVizPygountCacheCheckOnly -RepoRoot $RepoRoot -PythonExe $PythonExe
    if ($checkCode -eq 0) {
        Write-DashLog '[OK] Codebase Viz pygount-schijfcache aanwezig.' -Color DarkGray
        return $false
    }
    Write-DashLog '[INFO] Codebase Viz: pygount-cache opbouwen (eenmalig, kan tot 10 min duren)...' -Color Cyan
    Update-HermesLaunchActivity -Reason 'Codebase Viz: pygount-cache opbouwen (tot ~10 min)...'
    if ((Get-Command Test-HermesLaunchConsoleCapture -ErrorAction SilentlyContinue) -and (Test-HermesLaunchConsoleCapture)) {
        $warmCode = Invoke-HermesCapturedProcess -FilePath $PythonExe -ArgumentList @($warmScript) -Quiet -FilterNoise
        if ($warmCode -eq 0) {
            Write-DashLog '[OK] Codebase Viz pygount-cache opgebouwd vóór dashboard-start.' -Color Green
            return $true
        }
        Write-DashLog '[WARN] Codebase Viz pre-warm mislukt - dashboard bouwt cache later op.' -Color Yellow
        return $false
    }
    & $PythonExe $warmScript 2>&1 | ForEach-Object { Write-LaunchLogAppend $_ }
    if ($LASTEXITCODE -eq 0) {
        Write-DashLog '[OK] Codebase Viz pygount-cache opgebouwd vóór dashboard-start.' -Color Green
        return $true
    }
    Write-DashLog '[WARN] Codebase Viz pre-warm mislukt - dashboard bouwt cache later op.' -Color Yellow
    return $false
}

function Invoke-CodebaseVizWarmupScan {
    param(
        [string]$BindHost,
        [int]$BindPort,
        [string]$RepoRoot,
        [string]$PythonExe
    )
    if (-not $env:HERMES_BUNDLED_PLUGINS) { return }
    $warmup = 'auto'
    if ($null -ne $env:HERMES_CODEBASE_VIZ_WARMUP -and "$env:HERMES_CODEBASE_VIZ_WARMUP".Trim()) {
        $warmup = "$env:HERMES_CODEBASE_VIZ_WARMUP".Trim().ToLowerInvariant()
    }
    if ($warmup -in @('0', 'skip', 'off', 'false', 'no')) { return }
    if ($warmup -eq 'incremental') { return }

    $warmScript = Join-Path $RepoRoot 'scripts\warm_codebase_viz_pygount_cache.py'
    if ($PythonExe -and (Test-Path -LiteralPath $warmScript)) {
        & $PythonExe $warmScript --check-only 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-DashLog '[OK] Codebase Viz warmup: schijfcache actueel - force-scan overgeslagen.' -Color DarkGray
            return
        }
    }

    $connectHost = Get-DashboardConnectHost -BindHost $BindHost
    $base = "http://${connectHost}:${BindPort}"
    try {
        $html = (Invoke-WebRequest -Uri "${base}/codebase-viz" -UseBasicParsing -TimeoutSec 12).Content
    } catch {
        Write-DashLog '[WARN] Codebase Viz warmup: dashboard HTML niet bereikbaar.' -Color Yellow
        return
    }
    if ($html -notmatch '__HERMES_SESSION_TOKEN__="([^"]+)"') {
        Write-DashLog '[WARN] Codebase Viz warmup: geen session token in HTML.' -Color Yellow
        return
    }
    $token = $Matches[1]
    $scanUrl = "${base}/api/plugins/codebase-viz/force-scan"
    try {
        $null = Invoke-WebRequest -Uri $scanUrl -Method POST `
            -Headers @{ 'X-Hermes-Session-Token' = $token } `
            -UseBasicParsing -TimeoutSec 20
        Write-DashLog '[OK] Codebase Viz scan gestart (achtergrond, force-scan).' -Color Green
    } catch {
        Write-DashLog "[WARN] Codebase Viz force-scan: $($_.Exception.Message)" -Color Yellow
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

$vizInit = Initialize-WorkspaceDashboardPlugins -RepoRoot $RepoRoot
$vizDistRebuilt = $false
if ($vizInit) { $vizDistRebuilt = [bool]$vizInit.DistRebuilt }

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
    } catch {
        $null = $_.Exception.Message
    }
    finally {
        if ($null -ne $client) {
            try { $client.Close() } catch {
                $null = $_.Exception.Message
            }
        }
    }
    return $false
}

$workspacePlugins = [bool]$env:HERMES_BUNDLED_PLUGINS
$dashPyEarly = Get-DashboardPythonExe -RepoRoot $RepoRoot
$pipNeeded = Test-HermesNeedsWebDashboardPipInstall -RepoRoot $RepoRoot -RequirePygount:$workspacePlugins
$pygountCacheOk = $false
if ($workspacePlugins -and $dashPyEarly) {
    if (Test-HermesCodebaseVizPygountCacheMismatch -RepoRoot $RepoRoot) {
        [void](Clear-HermesCodebaseVizPygountCache -RepoRoot $RepoRoot -Reason 'pre-check')
    }
    $pygountCacheOk = (Invoke-HermesCodebaseVizPygountCacheCheckOnly -RepoRoot $RepoRoot -PythonExe $dashPyEarly) -eq 0
}

if ($workspacePlugins) {
    $dashboardAlreadyUp = Test-DashboardPortInUse -BindHost $hostAddr -BindPort $port
    $canSkipRestart = (-not $pipNeeded) -and (-not $vizDistRebuilt) -and $pygountCacheOk -and $dashboardAlreadyUp
    if ($canSkipRestart) {
        Write-DashLog ("[OK] Dashboard al actief; deps/cache ongewijzigd - http://${hostAddr}:${port}/sessions") -Color Green
        Open-DashboardBrowserIfRequested -BindHost $hostAddr -BindPort $port
        exit 0
    }
    if ($pipNeeded -or $vizDistRebuilt -or -not $pygountCacheOk) {
        Write-DashLog '[INFO] Workspace plugins: dashboard herstarten (deps, dist of pygount-cache gewijzigd).' -Color DarkGray
    } else {
        Write-DashLog '[INFO] Workspace plugins: dashboard herstarten.' -Color DarkGray
    }
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
        $statusArgs = Get-CondaDashboardRunArgs -PythonArgs @('dashboard', '--status')
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

$pipChanged = Install-HermesWebDashboardPackage -RepoRoot $RepoRoot

$dashPy = if ($dashPyEarly) { $dashPyEarly } else { Get-DashboardPythonExe -RepoRoot $RepoRoot }
[void](Ensure-CodebaseVizPygountCache -RepoRoot $RepoRoot -PythonExe $dashPy)

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
if (-not $dashPy) {
    Write-DashLog '[WARN] Dashboard niet gestart: geen hermes-env python.exe.' -Color Yellow
    exit 0
}
$argList = Get-HermesDashboardCliArgs -PythonArgs $dashPythonArgs

Write-DashLog "[INFO] Dashboard starten (geen browser): http://${hostAddr}:${port}/sessions" -Color Cyan
Write-DashLog ("[INFO] Python: $dashPy") -Color DarkGray
Write-DashLog ("[INFO] Log: $dashLog") -Color DarkGray

# Standaard Hidden + redirect (betrouwbaar op PS 5.1). Bij ghost-conhost/muisklik-blokkade:
# set HERMES_DASHBOARD_WINDOW_STYLE=normal of HERMES_DASHBOARD_USE_NOWINDOW=1 (Start-HermesNoWindowProcess).
$windowStyleRaw = ''
if ($null -ne $env:HERMES_DASHBOARD_WINDOW_STYLE) {
    $windowStyleRaw = "$env:HERMES_DASHBOARD_WINDOW_STYLE".Trim().ToLowerInvariant()
}
$useNoWindow = ($env:HERMES_DASHBOARD_USE_NOWINDOW -eq '1')
try {
    if ($useNoWindow) {
        $proc = Start-HermesNoWindowProcess `
            -FilePath $dashPy `
            -ArgumentList $argList `
            -WorkingDirectory $RepoRoot `
            -StandardOutputPath $dashLog `
            -StandardErrorPath $errLog
    } else {
        $ws = switch ($windowStyleRaw) {
            'minimized' { 'Minimized' }
            'normal' { 'Normal' }
            default { 'Hidden' }
        }
        $proc = Start-Process -FilePath $dashPy `
            -ArgumentList $argList `
            -WorkingDirectory $RepoRoot `
            -WindowStyle $ws `
            -PassThru `
            -RedirectStandardOutput $dashLog `
            -RedirectStandardError $errLog
    }
} catch {
    Write-DashLog ("[WARN] Dashboard start mislukt: $($_.Exception.Message)") -Color Yellow
    exit 0
}
if (-not $proc) {
    Write-DashLog '[WARN] Dashboard proces niet gestart.' -Color Yellow
    exit 0
}

Start-Sleep -Seconds 3
if ($proc.HasExited -and $proc.ExitCode -ne 0) {
    Write-DashLog ("[WARN] Dashboard stopte vroeg (exit $($proc.ExitCode)). Zie $dashLog en $errLog") -Color Yellow
    exit 0
}
if (Test-DashboardPortInUse -BindHost $hostAddr -BindPort $port) {
    Write-DashLog '[OK] Dashboard op de achtergrond.' -Color Green
    if ($env:HERMES_DASHBOARD_QUICK_START -ne '1') {
        $null = Test-CodebaseVizHealth -RepoRoot $RepoRoot -PythonExe $dashPy -BindHost $hostAddr -BindPort $port
    } else {
        Write-DashLog '[INFO] Quick start: /health-verify overgeslagen (HERMES_DASHBOARD_QUICK_START=1).' -Color DarkGray
    }
    Open-DashboardBrowserIfRequested -BindHost $hostAddr -BindPort $port
    exit 0
}
if (-not $proc.HasExited) {
    Write-DashLog '[OK] Dashboard start (build kan even duren).' -Color Green
    if ($env:HERMES_DASHBOARD_QUICK_START -ne '1') {
        $null = Test-CodebaseVizHealth -RepoRoot $RepoRoot -PythonExe $dashPy -BindHost $hostAddr -BindPort $port
    } else {
        Write-DashLog '[INFO] Quick start: /health-verify overgeslagen (HERMES_DASHBOARD_QUICK_START=1).' -Color DarkGray
    }
    Open-DashboardBrowserIfRequested -BindHost $hostAddr -BindPort $port
    exit 0
}
Write-DashLog ("[WARN] Poort ${port} nog niet bereikbaar. Zie $dashLog") -Color Yellow
exit 0
