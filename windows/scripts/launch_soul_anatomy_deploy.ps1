# Stamp-gestuurde SOUL anatomy deploy bij Hermes-start (13 domein-templates + snippets).
param(
    [string]$RepoRoot = '',
    [switch]$Force,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

if ($env:HERMES_SKIP_SOUL_DEPLOY_ON_START -eq '1') {
    if (-not $Quiet) {
        Write-Host '[INFO] SOUL anatomy deploy overgeslagen (HERMES_SKIP_SOUL_DEPLOY_ON_START=1).' -ForegroundColor DarkGray
    }
    exit 0
}

if ($env:HERMES_FORCE_SOUL_DEPLOY -eq '1') {
    $Force = $true
}

if (-not $RepoRoot) {
    if ($env:HERMES_REPO_ROOT) {
        $RepoRoot = $env:HERMES_REPO_ROOT.Trim().Trim('"')
    } else {
        $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    }
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$stampPath = Get-SoulAnatomyDeployStampPath
$needRun = Test-SoulAnatomyDeployNeeded -RepoRoot $RepoRoot -StampPath $stampPath -Force:$Force

if (-not $needRun) {
    if (-not $Quiet) {
        Write-Host '[INFO] SOUL anatomy up-to-date (stamp OK).' -ForegroundColor DarkGray
    }
    exit 0
}

if (-not $Quiet) {
    Write-Host '[INFO] SOUL anatomy deploy (13 domein-templates + snippets)...' -ForegroundColor Cyan
}

& (Join-Path $PSScriptRoot 'sync_all_domain_souls_from_templates.ps1') -RepoRoot $RepoRoot
if ($LASTEXITCODE -ne 0) {
    Write-Host '[ERROR] SOUL anatomy deploy mislukt.' -ForegroundColor Red
    exit 1
}

Set-SoulAnatomyDeployStamp -StampPath $stampPath
Set-InstitutionalNewChatReminder -Reason 'SOUL anatomy deploy bij start' -RepoRoot $RepoRoot

if (-not $Quiet) {
    Write-Host '[OK] SOUL anatomy deploy voltooid. Gebruik /new in Hermes.' -ForegroundColor Green
}
exit 0
