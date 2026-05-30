# Start web dashboard nadat Hermes-chat draait (niet blokkerend tijdens pre-chat).
# Aangeroepen via Start-HermesDashboardAfterChatDetached (CreateNoWindow; geen start /B / start ""). Uit: HERMES_DASHBOARD_AFTER_CHAT=0
param([string]$RepoRoot = '')

$ErrorActionPreference = 'SilentlyContinue'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

if ($env:HERMES_SKIP_DASHBOARD_ON_START -eq '1') { exit 0 }
if ($env:HERMES_DASHBOARD_ON_START -eq '0') { exit 0 }
if ($env:HERMES_DASHBOARD_AFTER_CHAT -eq '0') { exit 0 }

$env:HERMES_SKIP_DASHBOARD_BROWSER = '1'
Remove-Item Env:HERMES_DASHBOARD_OPEN_PATH -ErrorAction SilentlyContinue

if (-not $RepoRoot) {
    if ($env:HERMES_REPO_ROOT) { $RepoRoot = $env:HERMES_REPO_ROOT }
    else { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}
$env:HERMES_REPO_ROOT = $RepoRoot
if ($env:HERMES_DASHBOARD_USE_NOWINDOW -ne '0') {
    $env:HERMES_DASHBOARD_USE_NOWINDOW = '1'
}

$logPath = $env:HERMES_LAUNCH_LOG
if ($logPath) {
    Add-HermesLaunchLogLine -Message 'Deferred dashboard: wachten op chat-proces...'
}

function Test-HermesChatPythonRunning {
    try {
        $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction Stop
        foreach ($p in $procs) {
            $cmd = "$($p.CommandLine)"
            if ($cmd -match 'hermes_cli\.main' -and $cmd -notmatch 'dashboard') {
                return $true
            }
        }
    } catch {
        $null = $_.Exception.Message
    }
    return $false
}

$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
    if (Test-HermesChatPythonRunning) { break }
    Start-Sleep -Milliseconds 400
}

if (-not (Test-HermesChatPythonRunning)) {
    if ($logPath) {
        Add-HermesLaunchLogLine -Message 'Deferred dashboard: chat-proces niet gezien binnen 90s - overgeslagen.'
    }
    exit 0
}

# Korte pauze zodat prompt_toolkit/TUI de console heeft overgenomen.
Start-Sleep -Seconds 2
if ($logPath) {
    Add-HermesLaunchLogLine -Message 'Deferred dashboard: start launch_dashboard_on_start.ps1'
}

$dash = Join-Path $PSScriptRoot 'launch_dashboard_on_start.ps1'
if (-not (Test-Path -LiteralPath $dash)) { exit 1 }

$prevQuick = $env:HERMES_DASHBOARD_QUICK_START
$env:HERMES_DASHBOARD_QUICK_START = '1'
try {
    & $dash -RepoRoot $RepoRoot -Quiet
    exit $LASTEXITCODE
} finally {
    if ($null -eq $prevQuick) {
        Remove-Item Env:HERMES_DASHBOARD_QUICK_START -ErrorAction SilentlyContinue
    } else {
        $env:HERMES_DASHBOARD_QUICK_START = $prevQuick
    }
}
