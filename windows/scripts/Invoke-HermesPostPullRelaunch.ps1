#requires -Version 5.1
<#
.SYNOPSIS
  Stop Hermes/gateway, sync editable Python, clear update cache, repair gateway, relaunch in WT.

.DESCRIPTION
  Used after POST_GIT_PULL.bat or UPDATE_HERMES post-merge when -RelaunchHermes (default).
  Skips when HERMES_SKIP_RELAUNCH_AFTER_PULL=1.

.PARAMETER RepoRoot
  Hermes git checkout root.

.PARAMETER KeepPid
  Process IDs to keep (e.g. POST_GIT_PULL parent shell). Default: huidige PowerShell ($PID).

.PARAMETER InstallRag
  Also run pip install -e ".[rag]" after base editable install.
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = '',
    [int[]]$KeepPid = @(),
    [switch]$InstallRag,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$winDir = Split-Path -Parent $scriptDir
$script:RelaunchExitCode = 0

function Get-CondaExe {
    $candidates = @(
        (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
        (Join-Path $env:ProgramData 'anaconda3\Scripts\conda.exe'),
        (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe'),
        (Join-Path $env:ProgramData 'miniconda3\Scripts\conda.exe')
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) { return $c }
    }
    $cmd = Get-Command conda.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Invoke-HermesPipEditableInstall {
    param(
        [Parameter(Mandatory)][string]$PythonExe,
        [Parameter(Mandatory)][string]$Target,
        [string]$Label = 'pip install -e'
    )
    if (-not $Quiet) { Write-HermesInfo ($Label + ' ...') }
    & $PythonExe -m pip install -e $Target -q
    if ($LASTEXITCODE -ne 0) {
        Write-HermesWarn ($Label + ' mislukt (exit ' + $LASTEXITCODE + ')  - controleer REPAIR_PYTHON.bat')
        $script:RelaunchExitCode = 1
    }
}

. (Join-Path $winDir 'HermesShellCommon.ps1')
# Clear-HermesUpdateCheckCache lives in HermesShellCommon.ps1
. (Join-Path $winDir 'HermesNativeInvoke.ps1')
. (Join-Path $winDir 'HermesPythonPolicy.ps1')

if ($env:HERMES_SKIP_RELAUNCH_AFTER_PULL -eq '1') {
    if (-not $Quiet) { Write-HermesInfo 'Relaunch overgeslagen (HERMES_SKIP_RELAUNCH_AFTER_PULL=1).' }
    exit 0
}

try {
    if (-not $RepoRoot) {
        if ($env:HERMES_REPO_ROOT) {
            $RepoRoot = $env:HERMES_REPO_ROOT.Trim().Trim('"')
        } else {
            $RepoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
        }
    } else {
        $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
    }
} catch {
    Write-HermesFail ('Ongeldig RepoRoot: ' + $_.Exception.Message)
    exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot '.git'))) {
    Write-HermesWarn 'Geen git-checkout  - relaunch overgeslagen.'
    exit 0
}

if ($KeepPid.Count -eq 0) {
    $KeepPid = @($PID)
}

if (-not $Quiet) {
    Write-HermesInfo 'Hermes relaunch: gateway stop, processen stoppen, pip sync, WT-start...'
}

$conda = Get-CondaExe
if ($conda) {
    $gwStop = Invoke-HermesNativeCommand -FilePath $conda -ArgumentList @(
        'run', '-n', 'hermes-env', '--no-capture-output', 'hermes', 'gateway', 'stop'
    ) -Quiet
    if ((Test-NativeCommandFailed) -or ($gwStop -ne 0)) {
        Write-HermesWarn 'gateway stop gaf een waarschuwing (Hermes was mogelijk al gestopt).'
    }
}

$stopPs1 = Join-Path $winDir 'stop_other_hermes_processes.ps1'
if (Test-Path -LiteralPath $stopPs1) {
    $stopArgs = @()
    if ($Quiet) { $stopArgs += '-Quiet' }
    foreach ($keepId in $KeepPid) {
        if ($keepId -le 0) { continue }
        $stopArgs += '-KeepPid'
        $stopArgs += $keepId
    }
    & $stopPs1 @stopArgs
}

$py = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
if ($py -and (Test-Path -LiteralPath $py)) {
    Invoke-HermesPipEditableInstall -PythonExe $py -Target $RepoRoot -Label 'pip install -e .'
    if ($InstallRag) {
        Invoke-HermesPipEditableInstall -PythonExe $py -Target ($RepoRoot + '[rag]') -Label 'pip install -e ".[rag]"'
    }
} elseif (-not $Quiet) {
    Write-HermesWarn 'Geen Hermes Python gevonden  - pip sync overgeslagen.'
}

Clear-HermesUpdateCheckCache

try {
    Import-Module (Join-Path $scriptDir 'SyncSoulSnippet.psm1') -Force
    Set-InstitutionalNewChatReminder -Reason 'POST_GIT_PULL sync' -RepoRoot $RepoRoot -Quiet:$Quiet
} catch {
    Write-HermesWarn ('Kon new-chat reminder niet zetten: ' + $_.Exception.Message)
}

$repairGw = Join-Path $scriptDir 'repair_gateway_home.ps1'
if (Test-Path -LiteralPath $repairGw) {
    & $repairGw -Quiet:$Quiet
    if ($LASTEXITCODE -ne 0) {
        Write-HermesWarn 'repair_gateway_home.ps1 gaf een waarschuwing.'
    }
}

$env:HERMES_AUTO_NEW_AFTER_SYNC = '1'
try {
    Invoke-HermesLaunchInWindowsTerminal -RepoRoot $RepoRoot
    if (-not $Quiet) {
        Write-HermesOk 'Hermes gestart in nieuw Windows Terminal-tabblad (start_hermes via hermes_wt_entry.cmd).'
    }
} catch {
    Write-HermesWarn ("WT-start mislukt: $($_.Exception.Message)  - start handmatig start_hermes.bat")
    exit 1
}

if ($script:RelaunchExitCode -ne 0) {
    exit $script:RelaunchExitCode
}
exit 0
