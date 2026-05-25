<#
.SYNOPSIS
    Past hybrid auxiliary preset toe (Qwen/Ollama + Gemini vision) op runtime config.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$DryRun,
    [switch]$SkipOllamaCheck,
    [switch]$SetNewChatReminder
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
. (Join-Path $scriptDir 'HermesHomeCommon.ps1')

$repoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
$pyScript = Join-Path $scriptDir 'apply_auxiliary_hybrid_preset.py'

Initialize-UserHermesHomeRoot -FixUserEnv -Quiet | Out-Null

$conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
if (-not (Test-Path -LiteralPath $conda)) {
    $conda = Join-Path $env:ProgramData 'miniconda3\Scripts\conda.exe'
}
if (-not (Test-Path -LiteralPath $conda)) {
    Write-Host '[FAIL] conda niet gevonden' -ForegroundColor Red
    exit 1
}

$pyArgs = @($pyScript)
if ($DryRun) { $pyArgs += '--dry-run' }
if ($SkipOllamaCheck) { $pyArgs += '--skip-ollama-check' }

if ($PSCmdlet.ShouldProcess($env:HERMES_HOME, 'Apply auxiliary hybrid preset')) {
    & $conda run -n hermes-env --no-capture-output python @pyArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $DryRun -and ($SetNewChatReminder -or -not $PSBoundParameters.ContainsKey('SetNewChatReminder'))) {
    $syncMod = Join-Path $scriptDir 'SyncSoulSnippet.psm1'
    if (Test-Path -LiteralPath $syncMod) {
        Import-Module $syncMod -Force
        Set-InstitutionalNewChatReminder -Reason 'auxiliary hybrid preset applied' -RepoRoot $repoRoot -Quiet
    }
}

Write-Host '[OK] Auxiliary preset klaar — herstart Hermes (/new of launch_hermes.bat)' -ForegroundColor Green
exit 0
