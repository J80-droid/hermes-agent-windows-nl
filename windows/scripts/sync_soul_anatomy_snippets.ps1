# Canonieke SOUL anatomy snippet-sync (Values .. Memory) + duplicate Output repair.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$Force,
    [switch]$Verify,
    [switch]$SkipRepair,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

$suppressReminder = $false
if ($Quiet -and $env:HERMES_SUPPRESS_SOUL_REMINDER -ne '1') {
    $env:HERMES_SUPPRESS_SOUL_REMINDER = '1'
    $suppressReminder = $true
}

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$snippetSteps = @(
    , @('Values', 'sync_soul_values_snippet.ps1')
    , @('Interaction', 'sync_soul_interaction_snippet.ps1')
    , @('Out-format', 'sync_soul_output_format_snippet.ps1')
    , @('Trust', 'sync_soul_trust_verification_snippet.ps1')
    , @('Workflow', 'sync_soul_workflow_snippet.ps1')
    , @('Tool Usage', 'sync_soul_tool_governance_snippet.ps1')
    , @('Memory Policy', 'sync_soul_memory_policy_snippet.ps1')
    , @('Config governance', 'sync_soul_config_governance_snippet.ps1')
    , @('Codebase-audit', 'sync_soul_codebase_audit_snippet.ps1')
)

foreach ($entry in $snippetSteps) {
    $snippetLabel = $entry[0]
    $snippetFile = $entry[1]
    if (-not $Quiet) {
        Write-Host ('--- SOUL ' + $snippetLabel + ' ---') -ForegroundColor Cyan
    }
    $snippetArgs = @{
        RepoRoot   = $RepoRoot
        HermesRoot = $HermesRoot
    }
    if ($Verify) { $snippetArgs['Verify'] = $true }
    if ($Force) { $snippetArgs['Force'] = $true }
    $childScript = Join-Path $PSScriptRoot $snippetFile
    & $childScript @snippetArgs | Out-Null
    if (Test-NativeCommandFailed) {
        $exitCode = $LASTEXITCODE
        throw ('Snippet sync mislukt: ' + $snippetFile + ' (code ' + $exitCode + ')')
    }
}

if (-not $Verify -and -not $SkipRepair) {
    if (-not $Quiet) {
        Write-Host '--- Repair duplicate out-format blocks ---' -ForegroundColor Cyan
    }
    foreach ($path in (Get-SoulTargets -HermesRoot $HermesRoot)) {
        $content = Get-SoulFileContent -Path $path
        $fixed = Repair-SoulDuplicateOutputBlocks -Content $content
        if ($fixed -ne $content) {
            Set-SoulFileContent -Path $path -Content $fixed
            if (-not $Quiet) {
                Write-Host ('  REPAIR: ' + $path) -ForegroundColor Yellow
            }
        }
    }
}

if ($Force -and -not $Verify) {
    if ($Quiet) {
        Set-InstitutionalNewChatReminder -Reason 'SOUL anatomy snippet sync' -RepoRoot $RepoRoot -Quiet
    } else {
        Set-InstitutionalNewChatReminder -Reason 'SOUL anatomy snippet sync' -RepoRoot $RepoRoot
    }
}

if ($suppressReminder) {
    Remove-Item Env:HERMES_SUPPRESS_SOUL_REMINDER -ErrorAction SilentlyContinue
}

if (-not $Quiet) {
    Write-Host 'OK: SOUL anatomy snippets gesynchroniseerd.' -ForegroundColor Green
}
exit 0
