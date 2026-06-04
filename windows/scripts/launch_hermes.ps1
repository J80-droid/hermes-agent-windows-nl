# Pre-chat launch entry (Launch UI Sink) — aangeroepen vanuit launch_hermes.bat.
param(
    [string]$RepoRoot = '',
    [switch]$Setup,
    [switch]$RunInstitutionalE2E
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
[void](Invoke-HermesEnableConsoleAnsi)

if (-not $RepoRoot) {
    if ($env:HERMES_REPO_ROOT) { $RepoRoot = $env:HERMES_REPO_ROOT }
    else { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}
$env:HERMES_REPO_ROOT = $RepoRoot

. (Join-Path $PSScriptRoot 'Invoke-HermesOverlayBootstrap.ps1')
Invoke-HermesOverlayBootstrap -RepoRoot $RepoRoot

[void](Stop-HermesGhostInputBlockers -RepoRoot $RepoRoot)

Reset-HermesConsoleInputModes
Invoke-HermesDisableConsoleQuickEdit
try {
    if ($env:WT_SESSION) {
        [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    }
} catch { }
# bat heeft console al uitgevouwen (launch_hermes.bat) — dubbele expand veroorzaakt ghost-overlay
# Geen tweede Clear-Host in rich-modus: gele startbanner blijft zichtbaar tot orchestrator klaar is.
if ((Get-HermesLaunchUiMode) -ne 'rich') {
    try { Clear-Host } catch { }
}
Reset-HermesConsoleInputModes

if ($Setup -or $env:HERMES_RUN_FULL_SETUP_ON_LAUNCH -eq '1') {
    $setupPs1 = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'scripts/windows/setup_hermes_windows.ps1'
    if (-not (Test-Path -LiteralPath $setupPs1)) {
        Write-HermesLaunchUi -Message 'setup_hermes_windows.ps1 ontbreekt' -Level Error -ForceConsole
        exit 1
    }
    Write-HermesLaunchUi -Message 'Volledige setup (SETUP_HERMES / --setup)...' -Level Info -ForceConsole
    & $setupPs1
    exit $LASTEXITCODE
}

if ($env:HERMES_MINIMAL_LAUNCH -eq '1') {
    exit 0
}

if ($env:HERMES_LAUNCH_PROFILE) {
    if ((Get-HermesLaunchUiMode) -eq 'rich') {
        Add-HermesLaunchLogLine -Message ('INFO  Launch profile: ' + $env:HERMES_LAUNCH_PROFILE)
    } else {
        Write-HermesLaunchUi -Message ('Launch profile: ' + $env:HERMES_LAUNCH_PROFILE) -Level Info
    }
}

$isAdmin = $false
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} catch { }

if ($isAdmin) {
    $envMsg = 'Environment: Administrator'
} else {
    $envMsg = 'Environment: gebruiker (aanbevolen voor TrueColor in WT)'
}
if ((Get-HermesLaunchUiMode) -eq 'rich') {
    Add-HermesLaunchLogLine -Message ('INFO  ' + $envMsg)
    Add-HermesLaunchLogLine -Message 'INFO  Window State: Maximized'
    Add-HermesLaunchLogLine -Message ('INFO  Directory: ' + $RepoRoot)
    if ($env:HERMES_PYTHON) {
        Add-HermesLaunchLogLine -Message ('INFO  HERMES_PYTHON=' + $env:HERMES_PYTHON + ' (gateway / tool-subprocessen)')
    }
} else {
    Write-HermesLaunchUi -Message $envMsg -Level Info
    Write-HermesLaunchUi -Message 'Window State: Maximized' -Level Info
    Write-HermesLaunchUi -Message ('Directory: ' + $RepoRoot) -Level Info
    if ($env:HERMES_PYTHON) {
        Write-HermesLaunchUi -Message ('HERMES_PYTHON=' + $env:HERMES_PYTHON + ' (gateway / tool-subprocessen)') -Level Info
    }
}

$orchPath = Join-Path $PSScriptRoot 'launch_pre_chat_orchestrator.ps1'
$orchArgs = @{ RepoRoot = $RepoRoot }
if ($RunInstitutionalE2E) { $orchArgs['RunInstitutionalE2E'] = $true }
elseif ($env:HERMES_INSTITUTIONAL_E2E_ON_START -eq '1') { $orchArgs['RunInstitutionalE2E'] = $true }

try {
    & $orchPath @orchArgs
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = if ($?) { 0 } else { 1 } }
} finally {
    Stop-HermesLaunchActivity
}
exit [int]$code
