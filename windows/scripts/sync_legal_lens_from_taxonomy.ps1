# Sync ## Juridische lenzen in legal SOUL vanuit docs/LEGAL_TAXONOMY.md (template + runtime).
param(
    [string]$RepoRoot = '',
    [switch]$DryRun,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

if (-not $RepoRoot) {
    if ($env:HERMES_REPO_ROOT) { $RepoRoot = $env:HERMES_REPO_ROOT.Trim().Trim('"') }
    else { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

if ($env:HERMES_SKIP_LEGAL_LENS_SYNC -eq '1') {
    if (-not $Quiet) {
        Write-HermesLaunchUi -Message 'Legal lens sync overgeslagen (HERMES_SKIP_LEGAL_LENS_SYNC=1).' -Level Detail
    }
    exit 0
}

$python = $null
foreach ($candidate in @(
        $env:HERMES_PYTHON,
        (Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'),
        (Join-Path $env:USERPROFILE 'anaconda3\envs\hermes-env\python.exe')
    )) {
    if ($candidate -and (Test-Path -LiteralPath $candidate)) {
        $python = $candidate
        break
    }
}
if (-not $python) {
    $conda = Get-Command conda.exe -ErrorAction SilentlyContinue
    if ($conda) {
        $python = (& $conda.Source run -n hermes-env python -c "import sys; print(sys.executable)" 2>&1 |
            Select-Object -Last 1).Trim()
    }
}
if (-not $python -or -not (Test-Path -LiteralPath $python)) {
    Write-HermesLaunchUi -Message 'Legal lens sync: geen hermes-env python.' -Level Error -ForceConsole
    exit 1
}

$script = Join-Path $RepoRoot 'scripts\rag_pipeline\sync_legal_lens_table_from_taxonomy.py'
$args = @($script, '--all')
if ($DryRun) { $args += '--dry-run' }

if (-not $Quiet) {
    Write-HermesLaunchUi -Message 'Legal lenzentabel sync (LEGAL_TAXONOMY -> template + runtime)...' -Level Info
}

& $python @args
if (Test-NativeCommandFailed) {
    Write-HermesLaunchUi -Message ('Legal lens sync mislukt (exit ' + $LASTEXITCODE + ')') -Level Error -ForceConsole
    exit $LASTEXITCODE
}

if (-not $Quiet) {
    Write-HermesLaunchUi -Message 'Legal lenzentabel gesynchroniseerd.' -Level Ok
}
exit 0
