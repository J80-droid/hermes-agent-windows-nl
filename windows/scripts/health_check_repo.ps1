# Dagelijkse / handmatige repo-hygiene check (geen netwerk).
# Roept guard_git_clean.ps1 aan en rapporteert git-status samenvatting.
param(
    [string]$RepoRoot = '',
    [switch]$Strict
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

. (Join-Path $PSScriptRoot 'RepoHygieneCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = Resolve-HermesAgentRepoRoot -StartDir $PSScriptRoot
}

if (-not $RepoRoot) {
    Write-HermesErr 'Repo-root niet gevonden.'
    exit 2
}

Write-HermesInfo ('Health check repo: ' + $RepoRoot)

$guardScript = Join-Path $PSScriptRoot 'guard_git_clean.ps1'
if (-not (Test-Path -LiteralPath $guardScript)) {
    Write-HermesErr 'guard_git_clean.ps1 ontbreekt.'
    exit 2
}

$guardArgs = @{ RepoRoot = $RepoRoot }
if ($Strict) { $guardArgs['Strict'] = $true }
& $guardScript @guardArgs
if ($null -eq $LASTEXITCODE) {
    $guardCode = 0
} else {
    $guardCode = [int]$LASTEXITCODE
}

$porcelain = @(git -C $RepoRoot status --porcelain 2>$null | Where-Object { $_.Trim() })
Write-HermesInfo ('Git porcelain regels (totaal): ' + $porcelain.Count)

if ($guardCode -eq 0) {
    Write-HermesOk 'Repo-hygiene OK (guard).'
    exit 0
}

Write-HermesWarn ('Guard exit code: ' + $guardCode)
Write-HermesInfo 'Herstel: windows\UPDATE_HERMES.bat -QuickFix of docs\WORKSPACE_CONVENTIONS.md'
exit 1
