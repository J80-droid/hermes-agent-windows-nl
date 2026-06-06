# Hermes Agent — pytest vanaf repo-root (Windows, geen xdist)
# Draait dezelfde subset als CI (geen integration/e2e), serieel om xdist/PosixPath-problemen te vermijden.
# PowerShell-lint: aparte runner windows\tests\RUN_PSScriptAnalyzer.ps1 (of windows\audits\RUN_AUDITS.ps1).
$ErrorActionPreference = 'Stop'

$testsDir = $PSScriptRoot
$windowsDir = Split-Path -Parent $testsDir
$repoRoot = (Resolve-Path (Join-Path $windowsDir '..')).Path
Set-Location -LiteralPath $repoRoot

. (Join-Path $windowsDir 'HermesShellCommon.ps1')
. (Join-Path $windowsDir 'HermesPythonPolicy.ps1')
$py = Resolve-HermesPythonExe -RepoRoot $repoRoot -RequirePip
if (-not $py) {
    Write-Host 'ERROR: hermes-env python.exe niet gevonden. Draai windows\REPAIR_PYTHON.bat.' -ForegroundColor Red
    exit 1
}

$env:OPENROUTER_API_KEY = ''
$env:OPENAI_API_KEY = ''
$env:NOUS_API_KEY = ''
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
# Voorkomt dat stdout gebufferd blijft (Taakplanner / logs lijken dan "vast" rond ~50%).
$env:PYTHONUNBUFFERED = '1'

$pytestArgs = @(
    'tests/',
    '--ignore=tests/integration',
    '--ignore=tests/e2e',
    '--ignore=tests/docker',
    # git ls-files subprocess kan op grote Windows-worktrees >60s hangen (pytest-timeout).
    '--ignore=tests/gateway/test_complete_path_at_filter.py',
    '-m', 'not integration and not e2e',
    '-n', '0',
    '-q',
    '--tb=short',
    '--durations', '20'
)
$pytestArgs += $args

# Op Linux beperkt tests/conftest.py elke test tot ~30s (SIGALRM). Windows heeft dat niet:
# zonder pytest-timeout kan één hangende test de hele run laten lopen tot Taakbeheer / taak-timeout
# → afgebroken proces, vaak EXIT -1 / 4294967295.
#
# Timeout-aansturing: gebruik de officiële env **PYTEST_TIMEOUT** (pytest-timeout; seconden, 0 = uit).
# Alleen als die niet gezet is, voegen we **--timeout 60** toe — anders zou CLI altijd boven PYTEST_TIMEOUT gaan.
$null = & $py -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('pytest_timeout') else 1)" 2>$null
if ($LASTEXITCODE -eq 0) {
    $pytestTimeoutFromEnv = $null -ne $env:PYTEST_TIMEOUT -and $env:PYTEST_TIMEOUT -ne ''
    if (-not $pytestTimeoutFromEnv) {
        $pytestArgs = @('--timeout', '60') + $pytestArgs
    }
} else {
    Write-Host 'WAARSCHUWING: pytest-timeout ontbreekt in deze Python. Installeer: pip install pytest-timeout (of pip install -e ".[dev]" vanuit repo-root). Zonder timeout kunnen hangende tests op EXIT=-1 eindigen.' -ForegroundColor Yellow
}

$logPath = Join-Path $PSScriptRoot 'last_pytest_run.log'
Write-Host "Log: $logPath" -ForegroundColor DarkGray

Invoke-HermesAuditPytest -Python $py @pytestArgs 2>&1 | Tee-Object -FilePath $logPath
exit $LASTEXITCODE
