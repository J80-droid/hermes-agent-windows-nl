# Guard: waarschuwt bij ad-hoc scripts en data-bestanden in de repo-root.
#
# Doel: institutionele repo-hygiene — houdt de root schoon en dwingt gebruik
#       van output/ (genegeerd door git) of skills/ (herbruikbare vaardigheden)
#       af voor ad-hoc werk.
#
# Aanroepen: standalone of via upstream_sync.ps1 preflight.
# Dot-source HermesShellCommon indien beschikbaar voor PSES-tags.
param(
    [Parameter(Mandatory = $false)]
    [string]$RepoRoot = '',
    [switch]$Strict,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'

# Probeer HermesShellCommon te dot-sourcen voor consistente tags
$shellCommon = Join-Path $PSScriptRoot '..\HermesShellCommon.ps1'
if (-not (Test-Path -LiteralPath $shellCommon)) {
    $shellCommon = Join-Path (Split-Path -Parent $PSScriptRoot) 'HermesShellCommon.ps1'
}
if (Test-Path -LiteralPath $shellCommon) { . $shellCommon }

# Fallback logging als HermesShellCommon niet beschikbaar is
if (-not (Get-Command Write-HermesWarn -ErrorAction SilentlyContinue)) {
    function Write-HermesWarn { param([string]$Message) Write-Host ('WARN ' + $Message) }
    function Write-HermesInfo { param([string]$Message) Write-Host ('INFO ' + $Message) }
    function Write-HermesOk { param([string]$Message) Write-Host ('OK ' + $Message) }
    function Write-HermesErr { param([string]$Message) Write-Host ('ERROR ' + $Message) }
    function Test-NativeCommandFailed { return ($null -ne $LASTEXITCODE -and [int]$LASTEXITCODE -ne 0) }
}

# Repo-root bepalen
if (-not $RepoRoot) {
    $RepoRoot = & {
        $d = $PSScriptRoot
        while ($d) {
            if ((Test-Path (Join-Path $d 'pyproject.toml')) -and (Test-Path (Join-Path $d 'cli.py'))) {
                return (Resolve-Path -LiteralPath $d).Path
            }
            $next = Split-Path -Parent $d
            if (-not $next -or $next -eq $d) { break }
            $d = $next
        }
        return $null
    }
}

if (-not $RepoRoot) {
    Write-HermesErr 'Kan Hermes repo-root niet vinden.'
    exit 2
}

if (-not $Quiet) { Write-HermesInfo ('Repo-hygiene guard: ' + $RepoRoot) }

# Verzamel ongetrackte bestanden in de root (geen submappen)
try {
    $dirtyLines = @(git -C $RepoRoot status --porcelain 2>$null | Where-Object { $_.Trim() })
} catch {
    Write-HermesWarn 'git status --porcelain mislukt (niet in git-repo?).'
    exit 0
}

$rootFiles = @()

# Legitieme bestandsnamen in de root (allowlist)
$legitRoot = @(
    '.gitignore', '.cursorrules', '.env', 'pyproject.toml', 'package.json',
    'uv.lock', 'README.md', 'README-FORK.md', 'README.zh-CN.md',
    'AGENTS.md', 'cli.py', 'run_agent.py', 'model_tools.py', 'toolsets.py',
    'hermes_state.py', 'hermes_constants.py', 'hermes_logging.py',
    'hermes_bootstrap.py', 'hermes_time.py', 'batch_runner.py', 'config.yaml'
)

foreach ($line in $dirtyLines) {
    if (-not $line.Trim()) { continue }
    $raw = $line.TrimEnd()
    if ($raw -match ' -> ') {
        $path = ($raw -split ' -> ', 2)[-1].Trim()
    } elseif ($raw.Length -ge 4) {
        $path = $raw.Substring(3).Trim()
    } else {
        $path = $raw.Trim()
    }
    $norm = ($path -replace '\\', '/')

    # Alleen bestanden direct in de root (geen submappen)
    if ($norm -match '/') { continue }

    # Skip bekende root-bestanden die legitiem zijn
    if ($legitRoot -contains $norm) { continue }

    $rootFiles += $norm
}

if ($rootFiles.Count -eq 0) {
    if (-not $Quiet) { Write-HermesOk 'Repo-root schoon: geen ad-hoc scripts of data-bestanden.' }
    exit 0
}

# Categoriseer voor het rapport
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
Write-HermesInfo 'Conventie: output/ (genegeerd door git) of skills/ (herbruikbare vaardigheden).'
Write-HermesInfo 'Zie: docs/WORKSPACE_CONVENTIONS.md en AGENTS.md voor skill-authoring.'

if ($Strict) {
    Write-HermesErr ('Strict mode: repo-root niet schoon (' + $issueCount + ' bestanden).')
    exit 2
}

exit 0