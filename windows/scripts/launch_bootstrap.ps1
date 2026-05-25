# Lichtgewicht bootstrap bij Hermes-start (launch_hermes.bat) — geen volledige SETUP.
# launch_bootstrap.stamp wordt alleen bijgewerkt na succesvolle install_rag_extras ($ragOk).
param(
    [string]$RepoRoot = '',
    [switch]$ForceRagCheck
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$ensureEnv = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/ensure_hermes_launch_env.ps1'
if (Test-Path -LiteralPath $ensureEnv) {
    & $ensureEnv -FixUserEnv -SkipVerify
}

$stampFile = Sync-HermesLaunchBootstrapStamp
$pyproject = Join-Path $RepoRoot 'pyproject.toml'
$needRag = $ForceRagCheck.IsPresent

if (-not $needRag) {
    $needRag = Test-HermesNeedsRagExtrasInstall -RepoRoot $RepoRoot -PyprojectPath $pyproject
}

$ensurePy = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/ensure_hermes_python.ps1'
if (Test-Path -LiteralPath $ensurePy) {
    & $ensurePy -RepoRoot $RepoRoot -Quiet
}

if ($needRag) {
    $ragExtras = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/install_rag_extras.ps1'
    if (Test-Path -LiteralPath $ragExtras) {
        Write-Host '[INFO] RAG/MCP eenmalige sync (pyproject gewijzigd of eerste start)...' -ForegroundColor Cyan
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        & $ragExtras -RepoRoot $RepoRoot -Quiet
        $ragOk = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $prevEap
        if ($ragOk) {
            if (-not (Test-Path -LiteralPath (Split-Path -Parent $stampFile))) {
                New-Item -ItemType Directory -Path (Split-Path -Parent $stampFile) -Force | Out-Null
            }
            Set-Content -LiteralPath $stampFile -Value (Get-Date -Format 'o') -Encoding utf8
        } else {
            Write-Host '[WARN] RAG sync mislukt — stamp niet bijgewerkt; retry bij volgende start.' -ForegroundColor Yellow
        }
    }
}

exit 0
