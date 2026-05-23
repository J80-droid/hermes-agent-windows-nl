# Canonieke SOUL anatomy snippet-sync (Values → … → Memory) + duplicate Output repair.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$Force,
    [switch]$Verify,
    [switch]$SkipRepair,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
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

$scripts = @(
    @{ Name = 'Values'; File = 'sync_soul_values_snippet.ps1' },
    @{ Name = 'Interaction'; File = 'sync_soul_interaction_snippet.ps1' },
    @{ Name = 'Output'; File = 'sync_soul_output_format_snippet.ps1' },
    @{ Name = 'Trust'; File = 'sync_soul_trust_verification_snippet.ps1' },
    @{ Name = 'Workflow'; File = 'sync_soul_workflow_snippet.ps1' },
    @{ Name = 'Tool Usage'; File = 'sync_soul_tool_governance_snippet.ps1' },
    @{ Name = 'Memory Policy'; File = 'sync_soul_memory_policy_snippet.ps1' }
)

foreach ($item in $scripts) {
    if (-not $Quiet) {
        Write-Host "--- SOUL $($item.Name) ---" -ForegroundColor Cyan
    }
    $splat = @{
        RepoRoot    = $RepoRoot
        HermesRoot  = $HermesRoot
        Verify      = $Verify
    }
    if ($Force) { $splat['Force'] = $true }
    & (Join-Path $PSScriptRoot $item.File) @splat
    if ($LASTEXITCODE -ne 0) {
        throw "Snippet sync mislukt: $($item.File)"
    }
}

if (-not $Verify -and -not $SkipRepair) {
    if (-not $Quiet) {
        Write-Host '--- Repair duplicate Output blocks ---' -ForegroundColor Cyan
    }
    foreach ($path in (Get-SoulTargets -HermesRoot $HermesRoot)) {
        $content = Get-SoulFileContent -Path $path
        $fixed = Repair-SoulDuplicateOutputBlocks -Content $content
        if ($fixed -ne $content) {
            Set-SoulFileContent -Path $path -Content $fixed
            if (-not $Quiet) {
                Write-Host "  [REPAIR] $path" -ForegroundColor Yellow
            }
        }
    }
}

if ($Force -and -not $Verify) {
    Set-InstitutionalNewChatReminder -Reason 'SOUL anatomy snippet sync' -RepoRoot $RepoRoot -Quiet:$Quiet
}

if ($suppressReminder) {
    Remove-Item Env:HERMES_SUPPRESS_SOUL_REMINDER -ErrorAction SilentlyContinue
}

if (-not $Quiet) {
    Write-Host '[OK] SOUL anatomy snippets gesynchroniseerd.' -ForegroundColor Green
}
exit 0
