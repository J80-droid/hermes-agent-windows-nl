# Shared pytest runners driven by windows/tests/pytest_fork_gate.yaml (SSOT).
# Dot-source after HermesShellCommon.ps1 (Invoke-HermesAuditPytest, Get-HermesAuditPython).

function Initialize-HermesPytestRunEnv {
    param(
        [string]$HermesHome = ''
    )
    $env:OPENROUTER_API_KEY = ''
    $env:OPENAI_API_KEY = ''
    $env:NOUS_API_KEY = ''
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONUNBUFFERED = '1'
    if (-not $HermesHome) {
        $HermesHome = Join-Path $env:LOCALAPPDATA 'hermes'
    }
    $env:HERMES_HOME = $HermesHome
}

function Get-HermesPytestForkGateConfig {
    param(
        [Parameter(Mandatory)]
        [string]$RepoRoot,
        [ValidateSet('gate', 'upstream')]
        [string]$Mode = 'gate'
    )
    $loader = Join-Path $RepoRoot 'windows/scripts/load_pytest_fork_gate.py'
    if (-not (Test-Path -LiteralPath $loader)) {
        throw "manifest loader ontbreekt: $loader"
    }
    $py = Get-HermesAuditPython -RepoRoot $RepoRoot
    if (-not $py -or -not (Test-Path -LiteralPath $py)) {
        throw "python niet gevonden (Get-HermesAuditPython): $py"
    }
    $stderrFile = Join-Path ([System.IO.Path]::GetTempPath()) ("hermes_pytest_gate_loader_{0}.err" -f [Guid]::NewGuid().ToString('N'))
    try {
        $jsonRaw = & $py $loader --mode $Mode --repo-root $RepoRoot 2>$stderrFile
        if ($LASTEXITCODE -ne 0) {
            $errText = ''
            if (Test-Path -LiteralPath $stderrFile) {
                $errText = (Get-Content -LiteralPath $stderrFile -Raw -ErrorAction SilentlyContinue)
            }
            if (-not $errText) { $errText = ($jsonRaw | Out-String).Trim() }
            throw "load_pytest_fork_gate --mode $Mode faalde: $errText"
        }
        if (-not $jsonRaw) {
            throw "load_pytest_fork_gate --mode $Mode faalde: lege stdout"
        }
        return ($jsonRaw | ConvertFrom-Json)
    } catch {
        if ($_.Exception.Message -match '^load_pytest_fork_gate') {
            throw
        }
        throw "load_pytest_fork_gate --mode $Mode JSON parse faalde: $($_.Exception.Message)"
    } finally {
        Remove-Item -LiteralPath $stderrFile -Force -ErrorAction SilentlyContinue
    }
}

function Get-HermesPytestArgsFromConfig {
    param(
        [Parameter(Mandatory)]
        [psobject]$Config,
        [string[]]$ExtraArgs = @()
    )
    $pytestArgList = [System.Collections.Generic.List[string]]::new()
    foreach ($p in @($Config.paths)) {
        if ($p) { [void]$pytestArgList.Add([string]$p) }
    }
    foreach ($ig in @($Config.ignores)) {
        if ($ig) { [void]$pytestArgList.Add('--ignore=' + $ig) }
    }
    if ($Config.markers) {
        [void]$pytestArgList.Add('-m')
        [void]$pytestArgList.Add([string]$Config.markers)
    }
    foreach ($fixed in @('-n', '0', '-q', '--tb=short', '--durations', '20')) {
        [void]$pytestArgList.Add($fixed)
    }
    foreach ($ea in @($ExtraArgs)) {
        if ($null -eq $ea) { continue }
        $s = [string]$ea
        if ($s.Trim()) {
            [void]$pytestArgList.Add($s)
        }
    }
    return @($pytestArgList.ToArray())
}

function Invoke-HermesPytestGate {
    param(
        [Parameter(Mandatory)]
        [string]$RepoRoot,
        [string[]]$ExtraArgs = @()
    )
    Initialize-HermesPytestRunEnv
    $config = Get-HermesPytestForkGateConfig -RepoRoot $RepoRoot -Mode 'gate'
    $py = Get-HermesAuditPython -RepoRoot $RepoRoot
    if (-not $py -or -not (Test-Path -LiteralPath $py)) {
        Write-HermesErr 'python niet gevonden (Get-HermesAuditPython). Draai windows\REPAIR_PYTHON.bat.'
        $global:LASTEXITCODE = 1
        return
    }
    $argSplat = @{ Config = $config; ExtraArgs = $ExtraArgs }
    $pytestArgs = Get-HermesPytestArgsFromConfig @argSplat
    Invoke-HermesAuditPytest -Python $py @pytestArgs
    $global:LASTEXITCODE = $global:LASTEXITCODE
}

function Invoke-HermesPytestUpstream {
    param(
        [Parameter(Mandatory)]
        [string]$RepoRoot,
        [switch]$ReportOnly,
        [int]$MaxFail = 0,
        [string[]]$ExtraArgs = @()
    )
    Initialize-HermesPytestRunEnv
    $config = Get-HermesPytestForkGateConfig -RepoRoot $RepoRoot -Mode 'upstream'
    $py = Get-HermesAuditPython -RepoRoot $RepoRoot
    if (-not $py -or -not (Test-Path -LiteralPath $py)) {
        Write-HermesErr 'python niet gevonden (Get-HermesAuditPython). Draai windows\REPAIR_PYTHON.bat.'
        $global:LASTEXITCODE = 1
        return
    }
    $junitRel = [string]$config.junit
    $junitPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath ($junitRel -replace '\\', '/')
    $junitDir = Split-Path -Parent $junitPath
    if ($junitDir -and -not (Test-Path -LiteralPath $junitDir)) {
        New-Item -ItemType Directory -Force -Path $junitDir | Out-Null
    }
    $maxfail = if ($MaxFail -gt 0) { $MaxFail } else { [int]$config.maxfail }
    # String-interpolatie in @() — '+' in subexpressions plakt soms elementen op Windows PS 5.1.
    $upstreamExtra = @(
        "--maxfail=$maxfail"
        "--junitxml=$junitPath"
    )
    $mergedExtra = @($upstreamExtra) + @($ExtraArgs)
    $argSplat = @{ Config = $config; ExtraArgs = $mergedExtra }
    $pytestArgs = Get-HermesPytestArgsFromConfig @argSplat
    Invoke-HermesAuditPytest -Python $py @pytestArgs
    $pytestExit = $global:LASTEXITCODE

    $summarizer = Join-Path $RepoRoot 'windows/scripts/summarize_pytest_junit.py'
    if ((Test-Path -LiteralPath $summarizer) -and (Test-Path -LiteralPath $junitPath)) {
        $knownFails = Join-Path $RepoRoot 'windows/tests/pytest_upstream_known_fails.txt'
        $summaryOut = Join-Path $RepoRoot 'windows/tests/pytest_upstream_summary.json'
        $sumArgs = @($summarizer, '--junit', $junitPath, '--output', $summaryOut)
        if (Test-Path -LiteralPath $knownFails) {
            $sumArgs += @('--known-fails', $knownFails)
        }
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            & $py @sumArgs 2>&1 | Out-Host
        } finally {
            $ErrorActionPreference = $prevEap
        }
        if ($global:LASTEXITCODE -ne 0 -and -not $ReportOnly) {
            Write-HermesErr 'summarize_pytest_junit faalde; pytest exitcode blijft leidend.'
        }
    } elseif ($ReportOnly -and -not (Test-Path -LiteralPath $junitPath)) {
        Write-HermesErr "upstream junit ontbreekt: $junitPath"
    }

    if ($ReportOnly) {
        $global:LASTEXITCODE = 0
        return
    }
    $global:LASTEXITCODE = $pytestExit
}
