# E2E: platform_toolsets.cli per profiel vs docs/domain_toolsets.yaml + tool-count drempels.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = ''
)

$ErrorActionPreference = 'Stop'
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

function Get-HermesRoot {
    if ($HermesRoot) { return (Resolve-Path -LiteralPath $HermesRoot).Path }
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    return (Join-Path $env:USERPROFILE '.hermes')
}

Write-Host '=== Toolset domain E2E ===' -ForegroundColor Cyan

$py = $env:HERMES_PYTHON
if (-not $py) { $py = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe' }
if (-not (Test-Path -LiteralPath $py)) {
    Write-Host "[FAIL] Python niet gevonden: $py" -ForegroundColor Red
    exit 1
}

$checkScript = Join-Path $RepoRoot 'windows/scripts/sync_profile_toolsets_from_manifest.py'
$env:HERMES_HOME = Get-HermesRoot
& $py $checkScript --repo-root $RepoRoot --hermes-root $env:HERMES_HOME --check
if ($LASTEXITCODE -ne 0) {
    Write-Host '[FAIL] platform_toolsets.cli drift — draai SYNC_DOMAIN_TOOLSETS.bat' -ForegroundColor Red
    exit 1
}
Write-Host '[OK] platform_toolsets.cli matcht manifest (--check)' -ForegroundColor Green

$e2ePy = @"
import os, sys, yaml
from pathlib import Path
repo = Path(r'$RepoRoot')
hermes = Path(r'$env:HERMES_HOME')
sys.path.insert(0, str(repo))
manifest = yaml.safe_load((repo / 'docs/domain_toolsets.yaml').read_text(encoding='utf-8'))
profiles = manifest.get('profiles') or {}
required_base = {'mcp', 'file', 'memory', 'skills', 'clarify'}
failures = []
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
        failures.append(f'{name}: optional_toolsets staan in cli: {sorted(bad_opt)}')
    if 'hermes-cli' in cli or 'enabled_toolsets' in cfg:
        failures.append(f'{name}: hermes-cli of enabled_toolsets nog actief')
    max_tools = int(spec.get('max_tools') or 99)
    os.environ['HERMES_HOME'] = str(hermes / 'profiles' / name)
    from hermes_cli.tools_config import _get_platform_tools
    from model_tools import get_tool_definitions
    enabled = _get_platform_tools(cfg, 'cli')
    tools = get_tool_definitions(enabled_toolsets=enabled, quiet_mode=True)
    count = len(tools)
    if count > max_tools:
        failures.append(f'{name}: {count} tools > max {max_tools}')
    print(f'[OK] {name}: {count} tools (max {max_tools})')
root_cfg = hermes / 'config.yaml'
if root_cfg.is_file():
    root = yaml.safe_load(root_cfg.read_text(encoding='utf-8')) or {}
    pt = root.get('platform_toolsets') or {}
    if 'cli' not in pt:
        failures.append('root: platform_toolsets.cli ontbreekt (moet expliciet [])')
    root_cli = list(pt.get('cli') or [])
    if root.get('toolsets') and root.get('toolsets') != []:
        failures.append(f'root: toolsets moet [] zijn, is {root.get("toolsets")!r}')
    if root_cli != []:
        failures.append(f'root: platform_toolsets.cli moet [] zijn, is {root_cli!r}')
    else:
        print('[OK] root: platform_toolsets.cli expliciet leeg')
    os.environ['HERMES_HOME'] = str(hermes)
    from hermes_cli.tools_config import _get_platform_tools
    root_enabled = _get_platform_tools(root, 'cli')
    if 'hermes-cli' in root_enabled or len(root_enabled) > 3:
        failures.append(f'root: te veel toolsets zonder profiel ({sorted(root_enabled)})')
    else:
        print(f'[OK] root: {len(root_enabled)} toolset(s) zonder profiel (geen hermes-cli)')
if failures:
    for f in failures:
        print('[FAIL]', f)
    sys.exit(1)
print('[OK] Toolset domain E2E geslaagd')
"@

& $py -c $e2ePy
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host '[OK] Toolset domain E2E compleet' -ForegroundColor Green
exit 0
