# Stamp-gestuurde SOUL anatomy deploy bij Hermes-start (14 domein-templates + snippets).
param(
    [string]$RepoRoot = '',
    [switch]$Force,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

if ($env:HERMES_SKIP_SOUL_DEPLOY_ON_START -eq '1') {
    $skipMsg = 'SOUL anatomy deploy overgeslagen (HERMES_SKIP_SOUL_DEPLOY_ON_START=1).'
    Write-Output $skipMsg
    Write-HermesLaunchUi -Message $skipMsg -Level Info
    exit 0
}

if ($env:HERMES_FORCE_SOUL_DEPLOY -eq '1') { $Force = $true }

if (-not $RepoRoot) {
    if ($env:HERMES_REPO_ROOT) { $RepoRoot = $env:HERMES_REPO_ROOT.Trim().Trim('"') }
    else { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$stampPath = Get-SoulAnatomyDeployStampPath
$needRun = Test-SoulAnatomyDeployNeeded -RepoRoot $RepoRoot -StampPath $stampPath -Force:$Force

if (-not $needRun) {
    if (-not $Quiet) {
        Write-HermesLaunchUi -Message 'SOUL anatomy up-to-date (stamp OK).' -Level Detail
    }
    exit 0
}

Update-HermesLaunchActivity -Reason '14 domein-templates pushen...' -ProgressCurrent 0 -ProgressTotal 14
if (-not $Quiet) {
    Write-HermesLaunchUi -Message 'SOUL anatomy deploy (14 domein-templates + snippets)...' -Level Info
}

$syncScript = Join-Path $PSScriptRoot 'sync_all_domain_souls_from_templates.ps1'
if (Test-HermesLaunchConsoleCapture) {
    $syncCode = Invoke-HermesCapturedProcess -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $syncScript, '-RepoRoot', $RepoRoot
    ) -Quiet -FilterNoise
} else {
    & $syncScript -RepoRoot $RepoRoot
    $syncCode = [int]$LASTEXITCODE
}
if ($syncCode -ne 0) {
    Write-HermesLaunchUi -Message 'SOUL anatomy deploy mislukt.' -Level Error -ForceConsole
    exit 1
}

Set-SoulAnatomyDeployStamp -StampPath $stampPath
Set-InstitutionalNewChatReminder -Reason 'SOUL anatomy deploy bij start' -RepoRoot $RepoRoot

$verifyLegal = Join-Path $PSScriptRoot 'verify_legal_runtime.ps1'
if (Test-Path -LiteralPath $verifyLegal) {
    & $verifyLegal -RepoRoot $RepoRoot -Quiet
    if ((Test-NativeCommandFailed) -and ($env:HERMES_LEGAL_VERIFY_STRICT -eq '1')) {
        Write-HermesLaunchUi -Message 'Legal runtime verify mislukt (HERMES_LEGAL_VERIFY_STRICT=1).' -Level Error -ForceConsole
        exit 1
    }
}

$proactiveE2e = Join-Path $PSScriptRoot 'Invoke-LegalProactiveSparringE2E.ps1'
if (Test-Path -LiteralPath $proactiveE2e) {
    & $proactiveE2e -RepoRoot $RepoRoot -Context SoulDeploy -Quiet:$Quiet
    if (Test-NativeCommandFailed) {
        Write-HermesLaunchUi -Message 'Legal proactive sparring E2E mislukt na SOUL deploy.' -Level Error -ForceConsole
        exit 1
    }
}

if (-not $Quiet) {
    Write-HermesLaunchUi -Message 'SOUL anatomy deploy voltooid. Gebruik /new in Hermes.' -Level Ok
}
exit 0
