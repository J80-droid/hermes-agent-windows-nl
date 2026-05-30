# Lichtgewicht bootstrap bij Hermes-start (launch_hermes.bat) — geen volledige SETUP.
# Fast-path: launch_bootstrap.json + rag-deps.json → geen nested powershell voor ensure_*.
# Volledige run: ensure_hermes_launch_env + ensure_hermes_python + optioneel install_rag_extras.
param(
    [string]$RepoRoot = '',
    [switch]$ForceRagCheck,
    [switch]$ForceFull
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

if ($ForceFull) {
    $env:HERMES_FORCE_LAUNCH_BOOTSTRAP_FULL = '1'
}

$pyproject = Join-Path $RepoRoot 'pyproject.toml'
$stampFile = Sync-HermesLaunchBootstrapStamp

function Invoke-HermesBootstrapChildScript {
    param(
        [Parameter(Mandatory)][string]$ScriptPath,
        [hashtable]$Arguments = @{}
    )
    if (-not (Test-Path -LiteralPath $ScriptPath)) { return 0 }
    # In-process: scripts respecteren launch-capture (log i.p.v. console-spam); geen dubbele PS-cold-start.
    & $ScriptPath @Arguments
    if ($null -ne $LASTEXITCODE) { return [int]$LASTEXITCODE }
    return 0
}

$fastPath = $null
if (-not $ForceRagCheck.IsPresent) {
    $fastPath = Test-HermesLaunchBootstrapFastPath -RepoRoot $RepoRoot -PyprojectPath $pyproject
}

if ($fastPath -and $fastPath.Ok) {
    Invoke-HermesLaunchBootstrapQuickVerify -RepoRoot $RepoRoot -PythonExe $fastPath.PythonExe -FastPathReason $fastPath.Reason
    exit 0
}

if ($fastPath -and $fastPath.Reason -and (Get-Command Add-HermesLaunchLogLine -ErrorAction SilentlyContinue)) {
    Add-HermesLaunchLogLine -Message ('Bootstrap volledige controle: ' + $fastPath.Reason)
}

$ensureEnv = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/ensure_hermes_launch_env.ps1'
[void](Invoke-HermesBootstrapChildScript -ScriptPath $ensureEnv -Arguments @{
        FixUserEnv  = $true
        SkipVerify  = $true
    })

$needRag = $ForceRagCheck.IsPresent
if (-not $needRag) {
    $needRag = Test-HermesNeedsRagExtrasInstall -RepoRoot $RepoRoot -PyprojectPath $pyproject
}

$ensurePy = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/ensure_hermes_python.ps1'
$ensurePyCode = Invoke-HermesBootstrapChildScript -ScriptPath $ensurePy -Arguments @{
    RepoRoot = $RepoRoot
    Quiet    = $true
}
if ($ensurePyCode -ne 0) {
    Write-HermesLaunchUi -Message 'ensure_hermes_python mislukt — bootstrap afgebroken.' -Level Warn
    exit $ensurePyCode
}

$py = Get-HermesPreferredPython -RepoRoot $RepoRoot
$ragOk = -not $needRag

if ($needRag) {
    $ragExtras = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/install_rag_extras.ps1'
    if (Test-Path -LiteralPath $ragExtras) {
        Update-HermesLaunchActivity -Reason 'RAG extras installeren (conda pip)...'
        if (Test-HermesLaunchConsoleCapture) {
            $ragCode = Invoke-HermesBootstrapChildScript -ScriptPath $ragExtras -Arguments @{
                RepoRoot = $RepoRoot
                Quiet    = $true
            }
            $ragOk = ($ragCode -eq 0)
        } else {
            Write-HermesLaunchUi -Message 'RAG/MCP sync (pyproject gewijzigd of eerste start)...' -Level Info
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            $ragCode = Invoke-HermesBootstrapChildScript -ScriptPath $ragExtras -Arguments @{
                RepoRoot = $RepoRoot
                Quiet    = $true
            }
            $ragOk = ($ragCode -eq 0)
            $ErrorActionPreference = $prevEap
        }
        if (-not $ragOk) {
            Write-HermesLaunchUi -Message 'RAG sync mislukt — bootstrap-state niet bijgewerkt; retry bij volgende start.' -Level Warn
        }
    }
}

if ($ragOk -and $py) {
    [void](Write-HermesLaunchBootstrapState -RepoRoot $RepoRoot -PythonExe $py -PyprojectPath $pyproject)
}

exit 0
