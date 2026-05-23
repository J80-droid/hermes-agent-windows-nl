# E2E: platform_toolsets.cli per profiel vs docs/domain_toolsets.yaml + tool-count + pytest.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = ''
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

function Find-Conda {
    foreach ($p in @(
        (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
        (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe'),
        (Join-Path ${env:ProgramData} 'miniconda3\Scripts\conda.exe')
    )) {
        if ($p -and (Test-Path -LiteralPath $p)) { return $p }
    }
    return $null
}

function Get-HermesRoot {
    if ($HermesRoot) { return (Resolve-Path -LiteralPath $HermesRoot).Path }
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    return (Join-Path $env:USERPROFILE '.hermes')
}

function Get-AuditPython {
    if ($env:HERMES_PYTHON -and (Test-Path -LiteralPath $env:HERMES_PYTHON)) {
        return $env:HERMES_PYTHON
    }
    if ($env:HERMES_AUDIT_PYTHON -and (Test-Path -LiteralPath $env:HERMES_AUDIT_PYTHON)) {
        return $env:HERMES_AUDIT_PYTHON
    }
    $conda = Find-Conda
    if ($conda) {
        $out = & $conda run -n hermes-env python -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            return ($out | Select-Object -Last 1).ToString().Trim()
        }
    }
    $fallback = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if (Test-Path -LiteralPath $fallback) { return $fallback }
    return 'python'
}

$failures = 0
$reportLines = @(
    "# Toolset domain E2E",
    "",
    "Gestart: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "Repo: $RepoRoot",
    "Hermes: $(Get-HermesRoot)",
    ""
)

function Add-Report {
    param([string]$Line)
    $script:reportLines += $Line
}

function Step-Ok {
    param([string]$Name, [string]$Detail = '')
    Write-Host "[OK] $Name" -ForegroundColor Green
    if ($Detail) { Add-Report "- **$Name**: $Detail" } else { Add-Report "- **$Name**: OK" }
}

function Step-Fail {
    param([string]$Name, [string]$Detail)
    Write-Host "[FAIL] $Name — $Detail" -ForegroundColor Red
    Add-Report "- **$Name**: FAIL — $Detail"
    $script:failures++
}

$py = Get-AuditPython
if (-not (Test-Path -LiteralPath $py)) {
    Step-Fail 'python' "Niet gevonden: $py"
    exit 1
}

$hermes = Get-HermesRoot
$env:HERMES_HOME = $hermes
$logPath = Join-Path $scriptRoot 'TOOLSET_DOMAIN_E2E_LAST_RUN.log'

Write-Host '=== Toolset domain E2E (1/6 hermes home) ===' -ForegroundColor Cyan
$verifyHome = Join-Path $RepoRoot 'windows/scripts/verify_hermes_home.ps1'
if (Test-Path -LiteralPath $verifyHome) {
    & $verifyHome
    if ($LASTEXITCODE -ne 0) {
        Step-Fail 'verify_hermes_home' 'Zie verify_hermes_home.ps1'
    } else {
        Step-Ok 'verify_hermes_home'
    }
}

Write-Host '=== Toolset domain E2E (2/6 repo manifest) ===' -ForegroundColor Cyan
foreach ($rel in @(
    'docs/domain_toolsets.yaml',
    'docs/DOMAIN_TOOLSET_AUDIT.md',
    'docs/templates/SOUL_SHARED_TOOL_GOVERNANCE.md',
    'windows/scripts/sync_profile_toolsets_from_manifest.py',
    'windows/SYNC_DOMAIN_TOOLSETS.bat'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot $rel))) {
        Step-Fail 'repo-artefacten' "Ontbreekt: $rel"
    }
}
if ($failures -eq 0) { Step-Ok 'repo-artefacten' }

Write-Host '=== Toolset domain E2E (3/6 pytest subset) ===' -ForegroundColor Cyan
Push-Location $RepoRoot
try {
    & $py -m pytest `
        tests/windows/test_domain_toolsets_manifest.py `
        tests/hermes_cli/test_platform_toolsets_empty_cli.py `
        -q --tb=short 2>&1 | Tee-Object -Variable pytestOut | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Step-Fail 'pytest' "exit $LASTEXITCODE"
    } else {
        Step-Ok 'pytest' (($pytestOut | Select-Object -Last 1) -join ' ').Trim()
    }
} finally {
    Pop-Location
}

Write-Host '=== Toolset domain E2E (4/6 manifest drift --check) ===' -ForegroundColor Cyan
$checkScript = Join-Path $RepoRoot 'windows/scripts/sync_profile_toolsets_from_manifest.py'
& $py $checkScript --repo-root $RepoRoot --hermes-root $hermes --check 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Step-Fail 'manifest-check' 'Draai windows\SYNC_DOMAIN_TOOLSETS.bat'
} else {
    Step-Ok 'manifest-check' 'platform_toolsets.cli matcht manifest'
}

Write-Host '=== Toolset domain E2E (5/6 runtime tool-counts) ===' -ForegroundColor Cyan
$e2ePy = @"
import os, sys, yaml
from pathlib import Path
repo = Path(r'$RepoRoot')
hermes = Path(r'$hermes')
sys.path.insert(0, str(repo))
manifest = yaml.safe_load((repo / 'docs/domain_toolsets.yaml').read_text(encoding='utf-8'))
profiles = manifest.get('profiles') or {}
required_base = {'mcp', 'file', 'memory', 'skills', 'clarify'}
failures = []
profile_lines = []
for name, spec in sorted(profiles.items()):
    cfg_path = hermes / 'profiles' / name / 'config.yaml'
    if not cfg_path.is_file():
        failures.append(f'{name}: config.yaml ontbreekt')
        continue
    cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8')) or {}
    cli = set((cfg.get('platform_toolsets') or {}).get('cli') or [])
    expected = set((spec.get('platform_toolsets') or {}).get('cli') or [])
    if cli != expected:
        failures.append(f'{name}: cli mismatch {sorted(cli)} vs {sorted(expected)}')
    missing = required_base - cli
    if missing:
        failures.append(f'{name}: mist basis toolsets {sorted(missing)}')
    never = set(spec.get('never_default') or []) | set(manifest.get('never_default_global') or [])
    overlap = cli & never
    if overlap:
        failures.append(f'{name}: never_default in cli: {sorted(overlap)}')
    optional = set(spec.get('optional_toolsets') or [])
    bad_opt = optional & cli
    if bad_opt:
        failures.append(f'{name}: optional_toolsets in cli: {sorted(bad_opt)}')
    if 'hermes-cli' in cli or 'enabled_toolsets' in cfg:
        failures.append(f'{name}: hermes-cli of enabled_toolsets nog actief')
    max_tools = int(spec.get('max_tools') or 99)
    os.environ['HERMES_HOME'] = str(hermes / 'profiles' / name)
    from hermes_cli.tools_config import _get_platform_tools
    from model_tools import get_tool_definitions
    enabled = _get_platform_tools(cfg, 'cli')
    tools = get_tool_definitions(enabled_toolsets=enabled, quiet_mode=True)
    count = len(tools)
    profile_lines.append(f'{name}: {count} tools (max {max_tools})')
    if count > max_tools:
        failures.append(f'{name}: {count} tools > max {max_tools}')
root_cfg = hermes / 'config.yaml'
if root_cfg.is_file():
    root = yaml.safe_load(root_cfg.read_text(encoding='utf-8')) or {}
    pt = root.get('platform_toolsets') or {}
    if 'cli' not in pt:
        failures.append('root: platform_toolsets.cli ontbreekt')
    root_cli = list(pt.get('cli') or [])
    if root.get('toolsets') and root.get('toolsets') != []:
        failures.append(f'root: toolsets moet [] zijn')
    if root_cli != []:
        failures.append(f'root: cli moet [] zijn, is {root_cli!r}')
    os.environ['HERMES_HOME'] = str(hermes)
    from hermes_cli.tools_config import _get_platform_tools
    from model_tools import get_tool_definitions
    root_enabled = _get_platform_tools(root, 'cli')
    if 'hermes-cli' in root_enabled:
        failures.append('root: hermes-cli actief zonder profiel')
    root_tools = get_tool_definitions(enabled_toolsets=root_enabled, quiet_mode=True)
    if len(root_enabled) > 0 or len(root_tools) > 0:
        failures.append(f'root: {len(root_enabled)} toolsets / {len(root_tools)} tools — gebruik hermes -p <domein>')
    else:
        profile_lines.append('root: 0 toolsets, 0 tools')
if failures:
    for f in failures:
        print('[FAIL]', f)
    for line in profile_lines:
        print('[INFO]', line)
    sys.exit(1)
for line in profile_lines:
    print('[OK]', line)
print('[OK] runtime tool-counts')
"@

$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $runtimeOut = & $py -c $e2ePy 2>&1
    # Filter bekende non-fatale stderr patterns (auth.json, deprecation warnings, etc.)
    $filtered = $runtimeOut | Where-Object {
        $line = if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.ToString() } else { $_ }
        $line = $line.ToString()
        $isNonFatal = (
            $line -match 'auth: failed to parse' -or
            $line -match 'starting with empty store' -or
            $line -match 'Corrupt file preserved' -or
            $line -match 'DeprecationWarning' -or
            $line -match 'audioop' -or
            $line -match 'import audioop' -or
            $line -match 'site-packages.discord' -or
            $line -match 'NativeCommandError' -or
            $line -match '^At .*char\d+' -or
            $line -match '^\+\s+~' -or
            $line -match '^\s+\+' -or
            $line -match '^\s+~'
        )
        if ($isNonFatal) {
            Write-Host "[WARN] (non-fatal) $line" -ForegroundColor DarkGray
            return $false
        }
        return $true
    }
    $filtered | Out-Host
} finally {
    $ErrorActionPreference = $prevEap
}
if ($LASTEXITCODE -ne 0) {
    Step-Fail 'runtime-tool-counts' 'Zie console-output'
} else {
    $summary = ($runtimeOut | Where-Object { $_ -match '^\[OK\]' } | ForEach-Object { $_.ToString().Trim() }) -join '; '
    Step-Ok 'runtime-tool-counts' $summary
}

Write-Host '=== Toolset domain E2E (6/6 SOUL tool governance snippet) ===' -ForegroundColor Cyan
$snippet = Join-Path $RepoRoot 'docs/templates/SOUL_SHARED_TOOL_GOVERNANCE.md'
$missingSoul = @()
foreach ($name in @('core', 'legal', 'ict', 'security', 'dev', 'data')) {
    $soul = Join-Path $hermes "profiles\$name\SOUL.md"
    if (-not (Test-Path -LiteralPath $soul)) {
        $missingSoul += "${name}: SOUL ontbreekt"
        continue
    }
    $text = Get-Content -LiteralPath $soul -Raw -Encoding UTF8
    if ($text -notmatch 'Tool governance|optionele.*tool|Autonomy|Identity') {
        $missingSoul += "${name}: geen Tool governance in SOUL"
    }
}
if ($missingSoul.Count -gt 0) {
    $msg = ($missingSoul -join '; ') + ' — draai SYNC_TRUST_RUNTIME.bat of SYNC_SOUL_SNIPPETS.bat'
    Step-Fail 'soul-governance' $msg
} else {
    Step-Ok 'soul-governance' 'alle profielen (core, legal, ict, security, dev, data) bevatten tool-governance'
}

$reportLines += ''
if ($failures -gt 0) {
    $reportLines += "**Resultaat:** FAIL ($failures stap(pen))"
    $reportLines -join "`n" | Set-Content -LiteralPath $logPath -Encoding UTF8
    Write-Host "=== TOOLSET DOMAIN E2E: FAIL ($failures) ===" -ForegroundColor Red
    Write-Host "Rapport: $logPath" -ForegroundColor DarkGray
    exit 1
}

$reportLines += '**Resultaat:** PASS'
$reportLines -join "`n" | Set-Content -LiteralPath $logPath -Encoding UTF8
Write-Host '=== TOOLSET DOMAIN E2E: PASS ===' -ForegroundColor Green
Write-Host "Rapport: $logPath" -ForegroundColor DarkGray
exit 0
