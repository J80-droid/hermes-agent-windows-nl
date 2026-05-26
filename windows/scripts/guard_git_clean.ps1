# Guard: waarschuwt bij ad-hoc scripts en data-bestanden in de repo-root.
# Allowlist en pad-logica: RepoHygieneCommon.ps1 (gedeeld met quick_fix_repo_hygiene.ps1).
param(
    [string]$RepoRoot = '',
    [switch]$Strict,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'RepoHygieneCommon.ps1')

if (-not (Get-Command Write-HermesWarn -ErrorAction SilentlyContinue)) {
    function Write-HermesWarn { param([string]$Message) Write-Host ('WARN ' + $Message) }
    function Write-HermesInfo { param([string]$Message) Write-Host ('INFO ' + $Message) }
    function Write-HermesOk { param([string]$Message) Write-Host ('OK ' + $Message) }
    function Write-HermesErr { param([string]$Message) Write-Host ('ERROR ' + $Message) }
}

if (-not $RepoRoot) {
    $RepoRoot = Resolve-HermesAgentRepoRoot -StartDir $PSScriptRoot
}

if (-not $RepoRoot) {
    Write-HermesErr 'Kan Hermes repo-root niet vinden.'
    exit 2
}

if (-not $Quiet) { Write-HermesInfo ('Repo-hygiene guard: ' + $RepoRoot) }

$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$dirtyLines = @(git -C $RepoRoot status --porcelain 2>$null | Where-Object { $_.Trim() })
$ErrorActionPreference = $prevEap

if ($LASTEXITCODE -and [int]$LASTEXITCODE -ne 0 -and $dirtyLines.Count -eq 0) {
    Write-HermesWarn 'git status --porcelain mislukt (niet in git-repo?).'
    exit 0
}

$allowlist = @(Get-HermesRepoRootAllowlist)
$rootFiles = @()

foreach ($line in $dirtyLines) {
    if (-not $line.Trim()) { continue }
    $path = Get-GitPorcelainPath -Line $line
    if (Test-IsUnexpectedRepoRootEntry -Path $path -Allowlist $allowlist) {
        $rootFiles += ($path -replace '\\', '/')
    }
}

if ($rootFiles.Count -eq 0) {
    if (-not $Quiet) { Write-HermesOk 'Repo-root schoon: geen ad-hoc scripts of data-bestanden.' }
    exit 0
}

$scriptFiles = @($rootFiles | Where-Object { $_ -match '\.(py|ps1|sh|bat)$' })
$dataFiles = @($rootFiles | Where-Object { $_ -match '\.(xml|html|pdf|json|txt|csv|xlsx|docx|pptx|md)$' })
$otherFiles = @($rootFiles | Where-Object { $_ -notin $scriptFiles -and $_ -notin $dataFiles })
$issueCount = $rootFiles.Count

if ($scriptFiles.Count -gt 0) {
    Write-HermesWarn ('Scripts in repo-root (' + $scriptFiles.Count + '): ' + ($scriptFiles -join ', '))
    Write-HermesInfo '  Verplaats naar: output/research/scripts/ (tijdelijk) of skills/<categorie>/<naam>/scripts/ (herbruikbaar)'
}
if ($dataFiles.Count -gt 0) {
    Write-HermesWarn ('Data-bestanden in repo-root (' + $dataFiles.Count + '): ' + ($dataFiles -join ', '))
    Write-HermesInfo '  Verplaats naar: output/research/data/ of %USERPROFILE%\data\raw_source_files\'
}
if ($otherFiles.Count -gt 0) {
    Write-HermesWarn ('Overige bestanden in repo-root (' + $otherFiles.Count + '): ' + ($otherFiles -join ', '))
}

Write-HermesInfo ('Totaal onverwachte bestanden in repo-root: ' + $issueCount)
Write-HermesInfo 'Zie: docs/WORKSPACE_CONVENTIONS.md en AGENTS.md voor skill-authoring.'

if ($Strict) {
    Write-HermesErr ('Strict mode: repo-root niet schoon (' + $issueCount + ' bestanden).')
    exit 2
}

exit 0
