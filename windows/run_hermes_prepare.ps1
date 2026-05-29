. (Join-Path $PSScriptRoot 'HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'scripts\HermesHomeCommon.ps1')
# Voorbereiding voor Hermes chat: python, HERMES_HOME, launch state voor hermes_chat.cmd.
$ErrorActionPreference = 'Continue'
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } elseif ($MyInvocation.MyCommand.Path) {
    Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    (Get-Location).Path
}
$repoRoot = if ((Split-Path -Leaf $scriptRoot) -ieq 'windows') {
    (Resolve-Path (Join-Path $scriptRoot '..')).Path
} else {
    $scriptRoot
}
$logFile = Join-Path $repoRoot 'hermes_runtime.log'

function Write-RunLog {
    param([string]$Message, [string]$Level = 'INFO')
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "$ts [$Level] $Message"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

. (Join-Path $PSScriptRoot 'launch_profiles.ps1')

function Get-HermesCliArgs {
    return @(Get-HermesLaunchCliArgs -ArgumentList @($args))
}

if (Invoke-HermesEnsureInteractiveConsole -RepoRoot $repoRoot) {
    Write-RunLog 'Structurele herstart in cmd.exe (geen Win32-console-buffer).'
    exit 0
}

Reset-HermesConsoleInputModes
try { Clear-Host } catch { $null = $_.Exception.Message }
Set-HermesWin32ChatEnv -RepoRoot $repoRoot
[void](Stop-HermesGhostInputBlockers -RepoRoot $repoRoot)
Reset-HermesConsoleInputModes

$hermesPy = Get-HermesAuditPython -RepoRoot $repoRoot
if (-not $hermesPy -or -not (Test-Path -LiteralPath $hermesPy)) {
    Write-RunLog 'hermes-env python niet gevonden. Run windows\REPAIR_PYTHON.bat of zet HERMES_PYTHON.' 'ERROR'
    exit 1
}
Write-RunLog ('Python: ' + $hermesPy)

$ensureEnv = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/scripts/ensure_hermes_launch_env.ps1'
if (Test-Path -LiteralPath $ensureEnv) {
    & $ensureEnv -FixUserEnv
    if ($LASTEXITCODE -ne 0) {
        Write-RunLog "ensure_hermes_launch_env failed (exit $LASTEXITCODE)" 'ERROR'
        exit $LASTEXITCODE
    }
    Write-RunLog ('HERMES_HOME=' + $env:HERMES_HOME)
}

$envFile = Join-Path $repoRoot '.env'
$standardEnvFile = Join-Path $env:USERPROFILE '.hermes\.env'
$localAppDataEnv = Join-Path $env:LOCALAPPDATA 'hermes\.env'
$repoEnvExists = Test-Path -LiteralPath $envFile
$userHermesEnvExists = (Test-Path -LiteralPath $standardEnvFile) -or (Test-Path -LiteralPath $localAppDataEnv)

$cliArgs = @(Get-HermesCliArgs)
$chatMode = 'chat'
if ((-not $repoEnvExists) -and (-not $userHermesEnvExists)) {
    Write-RunLog 'First run detected: setup then chat.'
    $chatMode = 'setup_then_chat'
} else {
    Write-RunLog 'Launching Hermes Agent Chat...'
    if ($cliArgs.Count -gt 0) {
        Write-RunLog ('CLI args: ' + ($cliArgs -join ' '))
    }
}

Write-HermesLaunchState -PythonExe $hermesPy -RepoRoot $repoRoot -ChatMode $chatMode -CliArgs $cliArgs
. (Join-Path $PSScriptRoot 'scripts\HermesHomeCommon.ps1')
if ($env:HERMES_MINIMAL_LAUNCH -ne '1') {
    Write-Host '[INFO] Model/provider controleren (canonieke config)...' -ForegroundColor Cyan
}
if (-not (Invoke-HermesModelProviderCoherenceRepair -Quiet)) {
    Write-RunLog 'Model/provider coherence: zie OPEN_SETUP of REPAIR_MODEL_PROVIDER.bat' 'WARN'
}
try {
    $bust = @"
import sys
sys.path.insert(0, r'$repoRoot')
from hermes_cli.profile_model_inheritance import bust_config_caches, root_config_path
bust_config_caches(root_config_path())
"@
    $null = & $hermesPy -c $bust 2>&1
} catch {
    Write-RunLog ('Config-cache bust mislukt: ' + $_.Exception.Message) 'WARN'
}
if ($env:HERMES_MINIMAL_LAUNCH -ne '1') {
    Write-HermesRuntimeModelBanner
}
Invoke-HermesDisableConsoleQuickEdit
Reset-HermesConsoleInputModes
try { Clear-Host } catch { $null = $_.Exception.Message }
Write-Host '[INFO] Chat starten...' -ForegroundColor Green
exit 0
