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
    if (Test-HermesLaunchConsoleCapture) {
        [void](Invoke-HermesCapturedProcess -FilePath 'powershell.exe' -ArgumentList @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ensureEnv, '-FixUserEnv', '-SkipVerify'
        ) -Quiet -FilterNoise)
    } else {
        & $ensureEnv -FixUserEnv -SkipVerify
    }
}

$stampFile = Sync-HermesLaunchBootstrapStamp
$pyproject = Join-Path $RepoRoot 'pyproject.toml'
$needRag = $ForceRagCheck.IsPresent

if (-not $needRag) {
    $needRag = Test-HermesNeedsRagExtrasInstall -RepoRoot $RepoRoot -PyprojectPath $pyproject
}

$ensurePy = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/ensure_hermes_python.ps1'
if (Test-Path -LiteralPath $ensurePy) {
    if (Test-HermesLaunchConsoleCapture) {
        [void](Invoke-HermesCapturedProcess -FilePath 'powershell.exe' -ArgumentList @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ensurePy, '-RepoRoot', $RepoRoot, '-Quiet'
        ) -Quiet -FilterNoise)
    } else {
        & $ensurePy -RepoRoot $RepoRoot -Quiet
    }
}

if ($needRag) {
    $ragExtras = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/install_rag_extras.ps1'
    if (Test-Path -LiteralPath $ragExtras) {
        Update-HermesLaunchActivity -Reason 'RAG extras installeren (conda pip)...'
        if (Test-HermesLaunchConsoleCapture) {
            $ragCode = Invoke-HermesCapturedProcess -FilePath 'powershell.exe' -ArgumentList @(
                '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ragExtras, '-RepoRoot', $RepoRoot, '-Quiet'
            ) -Quiet -FilterNoise
            $ragOk = ($ragCode -eq 0)
        } else {
            Write-HermesLaunchUi -Message 'RAG/MCP eenmalige sync (pyproject gewijzigd of eerste start)...' -Level Info
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            & $ragExtras -RepoRoot $RepoRoot -Quiet
            $ragOk = ($LASTEXITCODE -eq 0)
            $ErrorActionPreference = $prevEap
        }
        if ($ragOk) {
            if (-not (Test-Path -LiteralPath (Split-Path -Parent $stampFile))) {
                New-Item -ItemType Directory -Path (Split-Path -Parent $stampFile) -Force | Out-Null
            }
            Set-Content -LiteralPath $stampFile -Value (Get-Date -Format 'o') -Encoding utf8
        } else {
            Write-HermesLaunchUi -Message 'RAG sync mislukt — stamp niet bijgewerkt; retry bij volgende start.' -Level Warn
        }
    }
}

exit 0
