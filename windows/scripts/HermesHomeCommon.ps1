# Gedeelde Hermes Windows home-paden (runtime vs legacy split-home).
# Dot-source: . (Join-Path $PSScriptRoot 'HermesHomeCommon.ps1')

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

function Test-HermesProfileSubdirPath {
    param([string]$Path)
    if (-not $Path) { return $false }
    $p = $Path.TrimEnd('\') -replace '/', '\'
    return $p -match '\\profiles\\[a-z0-9][a-z0-9_-]{0,63}$'
}

function Get-HermesLegacyRoot {
    return Join-Path $env:USERPROFILE '.hermes'
}

function Get-HermesRuntimeRoot {
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Get-HermesLegacyRoot
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

function Get-HermesCanonicalConfigPath {
    return Join-Path (Get-HermesRuntimeRoot) 'config.yaml'
}

function Get-HermesLegacyConfigPath {
    return Join-Path (Get-HermesLegacyRoot) 'config.yaml'
}

function Get-HermesConfigAuxiliaryFingerprint {
    param([string]$ConfigPath)
    if (-not (Test-Path -LiteralPath $ConfigPath)) { return $null }
    try {
        $raw = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8
        if ($raw -match '(?ms)^auxiliary:\s*(.+?)(?=^\S|\z)') {
            $block = $Matches[1]
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($block)
            $sha = [System.Security.Cryptography.SHA256]::Create()
            try {
                return [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant()
            } finally {
                $sha.Dispose()
            }
        }
    } catch {
        Write-Verbose $_.Exception.Message
    }
    return 'no-auxiliary-block'
}

function Get-HermesModelFieldsFromConfigYaml {
    <#
    .SYNOPSIS
        Leest model.provider en model.default uit config.yaml zonder regex (geen (?ms).* backtracking).
    #>
    param([string]$ConfigPath)
    $provider = ''
    $defaultModel = ''
    if (-not $ConfigPath -or -not (Test-Path -LiteralPath $ConfigPath)) {
        return [pscustomobject]@{ Provider = $provider; Default = $defaultModel }
    }
    $inModel = $false
    foreach ($line in [System.IO.File]::ReadLines($ConfigPath)) {
        if ($line -match '^\s*#') { continue }
        if ($line -match '^\s*$') { continue }
        if ($line -match '^model:\s*$') {
            $inModel = $true
            continue
        }
        if ($line -match '^model:\s*\S') {
            $inModel = $false
            continue
        }
        if ($inModel) {
            if ($line -match '^[^\s#]') {
                $inModel = $false
                continue
            }
            if ($line -match '^\s+provider:\s*(\S+)') {
                $provider = $Matches[1].Trim().Trim('"').Trim("'")
                continue
            }
            if ($line -match '^\s+default:\s*(\S+)') {
                $defaultModel = $Matches[1].Trim().Trim('"').Trim("'")
                continue
            }
        }
    }
    return [pscustomobject]@{ Provider = $provider; Default = $defaultModel }
}

function Write-HermesRuntimeModelBanner {
    <#
    .SYNOPSIS
        Toont canonieke runtime-config (één bron voor chat) — na setup/launch.
    #>
    $cfgPath = Get-HermesCanonicalConfigPath
    $legacyEnv = Join-Path (Get-HermesLegacyRoot) '.env'
    Write-Host '[INFO] Runtime-config (chat gebruikt dit bestand):' -ForegroundColor Cyan
    Write-Host ('       ' + $cfgPath) -ForegroundColor DarkGray
    Write-Host ('       Secrets hub: ' + $legacyEnv) -ForegroundColor DarkGray
    if (-not (Test-Path -LiteralPath $cfgPath)) {
        Write-Host '[WARN] config.yaml ontbreekt — run windows\OPEN_SETUP.bat' -ForegroundColor Yellow
        return
    }
    try {
        $fields = Get-HermesModelFieldsFromConfigYaml -ConfigPath $cfgPath
        $provider = $fields.Provider
        $model = $fields.Default
        if ($provider -or $model) {
            Write-Host ('[INFO] model.provider=' + $(if ($provider) { $provider } else { '?' })) -ForegroundColor Cyan
            Write-Host ('[INFO] model.default=' + $(if ($model) { $model } else { '?' })) -ForegroundColor Cyan
        }
        $authPath = Join-Path (Get-HermesRuntimeRoot) 'auth.json'
        if (Test-Path -LiteralPath $authPath) {
            $authRaw = Get-Content -LiteralPath $authPath -Raw -Encoding UTF8
            if ($authRaw -match '"active_provider"\s*:\s*"([^"]+)"') {
                Write-Host ('[INFO] auth.active_provider=' + $Matches[1]) -ForegroundColor Cyan
            }
        }
    } catch {
        Write-Host ('[WARN] Config lezen mislukt: ' + $_.Exception.Message) -ForegroundColor Yellow
    }
    Write-Host '[INFO] Wijzig provider via windows\OPEN_SETUP.bat (niet alleen .env keys).' -ForegroundColor DarkGray
}

function Invoke-HermesModelCatalogAutoRepair {
    param(
        [string]$RepoRoot = '',
        [switch]$Quiet
    )
    if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
        if ($env:HERMES_REPO_ROOT) { $RepoRoot = $env:HERMES_REPO_ROOT }
        else { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
    } else {
        $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
    }
    $repoRoot = $RepoRoot
    $python = Get-HermesAuditPython -RepoRoot $repoRoot
    if (-not $python) {
        if (-not $Quiet) { Write-HermesFail 'Geen Python voor model-catalog repair.' }
        return $false
    }
    $runtimeRoot = Get-HermesRuntimeRoot
    $code = @'
import os, sys
sys.path.insert(0, r'__REPO_ROOT__')
try:
    from overlay.bootstrap import install as _overlay_install
    _overlay_install()
except Exception:
    pass
os.environ['HERMES_HOME'] = r'__RUNTIME_ROOT__'
os.environ.setdefault('HERMES_WIN_PREFER_LOCALAPPDATA', '1')
from hermes_cli.config import load_config
from hermes_cli.models import (
    model_default_passes_startup_catalog_guard,
    model_matches_provider_catalog,
    normalize_provider,
    provider_model_ids,
)
from hermes_cli.model_runtime_config import persist_model_runtime

cfg = load_config() or {}
model = cfg.get('model') or {}
if isinstance(model, str):
    model = {'default': model}
provider = normalize_provider((model.get('provider') or '').strip())
default_model = (model.get('default') or model.get('model') or '').strip()
if not provider or provider in {'custom', 'auto'}:
    sys.exit(0)
if model_default_passes_startup_catalog_guard(provider, default_model):
    sys.exit(0)
catalog = list(provider_model_ids(provider) or [])
if not catalog:
    sys.exit(1)
pick = catalog[0]
if default_model and model_matches_provider_catalog(default_model, catalog):
    for mid in catalog:
        if model_matches_provider_catalog(default_model, [mid]):
            pick = mid
            break
persist_model_runtime(provider, default_model=pick, sync_auth=True)
print(f'ok: model.default -> {pick}')
sys.exit(0)
'@
    $code = $code.Replace('__REPO_ROOT__', $repoRoot.Replace('\', '\\'))
    $code = $code.Replace('__RUNTIME_ROOT__', $runtimeRoot.Replace('\', '\\'))
    $tmpPy = Join-Path ([System.IO.Path]::GetTempPath()) ("hermes_catalog_repair_" + [Guid]::NewGuid().ToString('N') + '.py')
    try {
        Set-Content -LiteralPath $tmpPy -Value $code -Encoding UTF8
        $output = & $python $tmpPy 2>&1
        if ($LASTEXITCODE -ne 0) {
            if (-not $Quiet) {
                foreach ($line in @($output)) { if ($line) { Write-HermesFail $line } }
            }
            return $false
        }
        if (-not $Quiet) { Write-HermesOk 'Model-catalog auto-repair toegepast.' }
        return $true
    } finally {
        Remove-Item -LiteralPath $tmpPy -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-HermesModelProviderCoherenceRepair {
    param([switch]$Quiet)
    $repairScript = Join-Path $PSScriptRoot 'repair_model_provider_coherence.ps1'
    if (-not (Test-Path -LiteralPath $repairScript)) {
        if (-not $Quiet) {
            Write-HermesFail "Repair script ontbreekt: $repairScript"
        }
        return $false
    }
    try {
        $null = & $repairScript -Quiet 2>&1
        return ($LASTEXITCODE -eq 0)
    } catch {
        if (-not $Quiet) {
            Write-HermesFail "Model/provider repair mislukt: $($_.Exception.Message)"
        }
        return $false
    }
}

function Test-HermesConfigDrift {
    param(
        [switch]$Strict,
        [switch]$Quiet,
        [switch]$AutoRepairModelProvider
    )
    $runtimeCfg = Get-HermesCanonicalConfigPath
    $legacyCfg = Get-HermesLegacyConfigPath
    $issues = [System.Collections.Generic.List[string]]::new()

    if (-not (Test-Path -LiteralPath $runtimeCfg)) {
        $issues.Add("Runtime config ontbreekt: $runtimeCfg")
    }

    if (Test-Path -LiteralPath $legacyCfg) {
        $deprecated = Get-ChildItem -LiteralPath (Get-HermesLegacyRoot) -Filter 'config.yaml.deprecated-*' -File -ErrorAction SilentlyContinue
        $readme = Join-Path (Get-HermesLegacyRoot) 'CONFIG_README.txt'
        if (Test-Path -LiteralPath $runtimeCfg) {
            $rtFp = Get-HermesConfigAuxiliaryFingerprint -ConfigPath $runtimeCfg
            $lgFp = Get-HermesConfigAuxiliaryFingerprint -ConfigPath $legacyCfg
            if ($rtFp -ne $lgFp) {
                $issues.Add("Config drift: legacy ~/.hermes/config.yaml wijkt af van runtime (auxiliary fingerprint)")
            }
        }
        if ($Strict -and -not (Test-Path -LiteralPath $readme) -and -not $deprecated) {
            $issues.Add('Legacy config.yaml bestaat nog — run APPLY_HERMES_HOME_MIGRATION.bat of DEPRECATE_LEGACY_CONFIG.bat')
        }
    }

    if ($issues.Count -eq 0) {
        $profileIssues = Test-HermesProfileGlobalConfigBlocks -Quiet:$Quiet
        foreach ($pi in $profileIssues) { $issues.Add($pi) }
    }

    if ($issues.Count -eq 0) {
        if (-not (Test-HermesModelProviderCoherence -Quiet:$Quiet)) {
            if ($AutoRepairModelProvider) {
                if (-not $Quiet) {
                    Write-HermesWarn 'Model/provider incoherentie — auto-repair (eenmalig)...'
                }
                if (Invoke-HermesModelProviderCoherenceRepair -Quiet:$Quiet) {
                    if (Test-HermesModelProviderCoherence -Quiet:$Quiet) {
                        if (-not $Quiet) {
                            Write-HermesOk 'Model/provider incoherentie hersteld via auto-repair'
                        }
                    } else {
                        $issues.Add(
                            'Model/provider incoherentie blijft na auto-repair — run windows\REPAIR_MODEL_PROVIDER.bat of hermes doctor --fix'
                        )
                    }
                } else {
                    $issues.Add(
                        'Model/provider auto-repair mislukt — run windows\REPAIR_MODEL_PROVIDER.bat of hermes doctor --fix'
                    )
                }
            } else {
                $issues.Add(
                    'Model/provider incoherentie (auth.json vs config) — run windows\REPAIR_MODEL_PROVIDER.bat of hermes doctor --fix'
                )
            }
        }
    }

    if ($issues.Count -eq 0) {
        if (-not (Test-HermesModelCatalogAvailability -Quiet:$Quiet)) {
            if (Invoke-HermesModelCatalogAutoRepair -Quiet:$Quiet) {
                if (Test-HermesModelCatalogAvailability -Quiet:$Quiet) {
                    if (-not $Quiet) {
                        Write-HermesOk 'Model-catalog hersteld via auto-repair'
                    }
                } else {
                    $issues.Add(
                        'Model/default staat niet in provider-catalog - run hermes model (of pas model.provider + model.default aan).'
                    )
                }
            } else {
                $issues.Add(
                    'Model/default staat niet in provider-catalog - run hermes model (of pas model.provider + model.default aan).'
                )
            }
        }
    }

    if ($issues.Count -eq 0) {
        if (-not $Quiet) {
            Write-HermesOk 'Geen config drift (split-home)'
        }
        Test-HermesAuxiliaryPresetDrift -Quiet:$Quiet | Out-Null
        return $true
    }

    foreach ($issue in $issues) {
        if (-not $Quiet) {
            Write-HermesFail $issue
        }
    }
    return $false
}

function Test-HermesModelProviderCoherence {
    param([switch]$Quiet)
    $configPath = Get-HermesCanonicalConfigPath
    if (-not (Test-Path -LiteralPath $configPath)) {
        return $true
    }
    try {
        $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
        $runtimeRoot = Get-HermesRuntimeRoot
        $python = Get-HermesAuditPython -RepoRoot $repoRoot
        $code = @"
import os, sys
sys.path.insert(0, r'$repoRoot')
try:
    from overlay.bootstrap import install as _overlay_install
    _overlay_install()
except Exception:
    pass
os.environ['HERMES_HOME'] = r'$runtimeRoot'
os.environ.setdefault('HERMES_WIN_PREFER_LOCALAPPDATA', '1')
from hermes_cli.config import load_config
from hermes_cli.model_runtime_config import detect_model_provider_incoherence
issues = detect_model_provider_incoherence(load_config())
errors = [i for i in issues if getattr(i, 'severity', 'warn') == 'error']
if not errors:
    sys.exit(0)
for i in errors:
    print(f'{i.severity}: {i.message}')
sys.exit(1)
"@
        $output = & $python -c $code 2>&1
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            if (-not $Quiet) {
                foreach ($line in @($output)) {
                    if ($line) { Write-HermesFail $line }
                }
            }
            return $false
        }
        return $true
    } catch {
        if (-not $Quiet) {
            Write-HermesFail "Model/provider coherence check mislukt: $($_.Exception.Message)"
        }
        return $false
    }
}

# Startup guard: model.default vs provider catalog (live /models when OAuth works,
# :free variant suffixes, else validate_requested_model — see model_default_passes_startup_catalog_guard).
function Test-HermesModelCatalogAvailability {
    param([switch]$Quiet)
    $configPath = Get-HermesCanonicalConfigPath
    if (-not (Test-Path -LiteralPath $configPath)) {
        return $true
    }
    try {
        $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
        $runtimeRoot = Get-HermesRuntimeRoot
        $python = Get-HermesAuditPython -RepoRoot $repoRoot
        if (-not $python) {
            if (-not $Quiet) { Write-HermesFail 'Geen Python voor model/catalog check (conda of .venv).' }
            return $false
        }
        $code = @'
import os
import sys
sys.path.insert(0, r'__REPO_ROOT__')
try:
    from overlay.bootstrap import install as _overlay_install
    _overlay_install()
except Exception:
    pass
os.environ['HERMES_HOME'] = r'__RUNTIME_ROOT__'
os.environ.setdefault('HERMES_WIN_PREFER_LOCALAPPDATA', '1')
from hermes_cli.config import load_config
from hermes_cli.models import (
    model_default_passes_startup_catalog_guard,
    normalize_provider,
    provider_model_ids,
)

cfg = load_config() or {}
model = cfg.get('model') or {}
if isinstance(model, str):
    model = {'default': model}
provider = normalize_provider((model.get('provider') or '').strip())
default_model = (model.get('default') or model.get('model') or '').strip()
if not provider or not default_model:
    sys.exit(0)
if provider in {'custom', 'auto'}:
    sys.exit(0)

if model_default_passes_startup_catalog_guard(provider, default_model):
    sys.exit(0)

catalog = list(provider_model_ids(provider) or [])
print(f"error: model '{default_model}' staat niet in catalog voor provider '{provider}'")
sample = ', '.join(catalog[:8])
if sample:
    print(f"hint: voorbeelden: {sample}")
sys.exit(1)
'@
        $code = $code.Replace('__REPO_ROOT__', $repoRoot.Replace('\', '\\'))
        $code = $code.Replace('__RUNTIME_ROOT__', $runtimeRoot.Replace('\', '\\'))
        $tmpPy = Join-Path ([System.IO.Path]::GetTempPath()) ("hermes_model_catalog_guard_" + [System.Guid]::NewGuid().ToString("N") + ".py")
        Set-Content -LiteralPath $tmpPy -Value $code -Encoding UTF8
        try {
            $output = & $python $tmpPy 2>&1
        } finally {
            Remove-Item -LiteralPath $tmpPy -Force -ErrorAction SilentlyContinue
        }
        if ($LASTEXITCODE -ne 0) {
            if (-not $Quiet) {
                foreach ($line in @($output)) {
                    if ($line) { Write-HermesFail $line }
                }
            }
            return $false
        }
        return $true
    } catch {
        if (-not $Quiet) {
            Write-HermesFail "Model/catalog check mislukt: $($_.Exception.Message)"
        }
        return $false
    }
}


function Test-HermesProfileGlobalConfigBlocks {
    param([switch]$Quiet)
    $issues = [System.Collections.Generic.List[string]]::new()
    $profilesRoot = Join-Path (Get-HermesRuntimeRoot) 'profiles'
    if (-not (Test-Path -LiteralPath $profilesRoot)) { return @() }
    foreach ($dir in Get-ChildItem -LiteralPath $profilesRoot -Directory) {
        $cfg = Join-Path $dir.FullName 'config.yaml'
        if (-not (Test-Path -LiteralPath $cfg)) { continue }
        $raw = Get-Content -LiteralPath $cfg -Raw -Encoding UTF8
        if ($raw -match '(?m)^auxiliary:\s*') {
            $issues.Add("Profiel '$($dir.Name)' heeft eigen auxiliary - hoort in root config (strip_profile_global_config_blocks.py)")
        }
        if ($raw -match '(?m)^providers:\s*' -or $raw -match '(?m)^custom_providers:\s*') {
            $issues.Add("Profiel '$($dir.Name)' heeft eigen providers - hoort in root config")
        }
    }
    if ($issues.Count -gt 0 -and -not $Quiet) {
        foreach ($issue in $issues) {
            Write-HermesFail $issue
        }
    }
    return @($issues)
}

function Test-HermesVeniceProviderConfigured {
    param([switch]$Quiet)
    $runtimeCfg = Get-HermesCanonicalConfigPath
    if (-not (Test-Path -LiteralPath $runtimeCfg)) { return $true }
    $raw = Get-Content -LiteralPath $runtimeCfg -Raw -Encoding UTF8
    if ($raw -match '(?m)^\s+venice:') { return $true }
    $legacyRoot = Get-HermesLegacyRoot
    $best = $null
    $bestSize = 0
    foreach ($pat in @('config.yaml.bak.*', 'config.yaml.deprecated-*')) {
        foreach ($f in Get-ChildItem -LiteralPath $legacyRoot -Filter $pat -File -ErrorAction SilentlyContinue) {
            if ($f.Length -gt $bestSize) { $bestSize = $f.Length; $best = $f.FullName }
        }
    }
    if (-not $best) { return $true }
    $legacyRaw = Get-Content -LiteralPath $best -Raw -Encoding UTF8
    if ($legacyRaw -notmatch '(?m)^providers:\s*\r?\n\s+venice:') { return $true }
    if (-not $Quiet) {
        Write-HermesWarn 'Venice provider ontbreekt in runtime config - run merge_legacy_providers_config.py'
    }
    return $false
}

function Test-HermesJatevoProviderConfigured {
    param([switch]$Quiet)
    $runtimeCfg = Get-HermesCanonicalConfigPath
    if (-not (Test-Path -LiteralPath $runtimeCfg)) { return $true }
    $raw = Get-Content -LiteralPath $runtimeCfg -Raw -Encoding UTF8
    if ($raw -match '(?m)^\s+jatevo:') { return $true }
    $legacyRoot = Get-HermesLegacyRoot
    $best = $null
    $bestSize = 0
    foreach ($pat in @('config.yaml.bak.*', 'config.yaml.deprecated-*')) {
        foreach ($f in Get-ChildItem -LiteralPath $legacyRoot -Filter $pat -File -ErrorAction SilentlyContinue) {
            if ($f.Length -gt $bestSize) { $bestSize = $f.Length; $best = $f.FullName }
        }
    }
    if (-not $best) { return $true }
    $legacyRaw = Get-Content -LiteralPath $best -Raw -Encoding UTF8
    if ($legacyRaw -notmatch '(?m)^providers:\s*\r?\n\s+jatevo:') { return $true }
    if (-not $Quiet) {
        Write-HermesWarn 'Jatevo provider ontbreekt in runtime config - run merge_legacy_providers_config.py'
    }
    return $false
}

function Initialize-UserHermesHomeRoot {
    param(
        [switch]$FixUserEnv,
        [switch]$Quiet
    )
    $root = (Get-HermesRuntimeRoot).TrimEnd('\')
    $changed = $false

    $userHome = [Environment]::GetEnvironmentVariable('HERMES_HOME', 'User')
    if ($userHome -and (Test-HermesProfileSubdirPath $userHome)) {
        if (-not $Quiet) {
            Write-HermesWarn ('User HERMES_HOME wijst naar profielmap: ' + $userHome)
        }
        if ($FixUserEnv) {
            [Environment]::SetEnvironmentVariable('HERMES_HOME', $root, 'User')
            $changed = $true
        }
    } elseif (-not $userHome -or ($userHome.TrimEnd('\') -ne $root)) {
        if ($FixUserEnv) {
            [Environment]::SetEnvironmentVariable('HERMES_HOME', $root, 'User')
            $changed = $true
        } elseif (-not $Quiet -and -not $userHome) {
            Write-HermesInfo ('User HERMES_HOME niet gezet — runtime root: ' + $root)
        }
    }

    if ($env:HERMES_HOME -and (Test-HermesProfileSubdirPath $env:HERMES_HOME)) {
        $env:HERMES_HOME = $root
        $changed = $true
    } elseif (-not $env:HERMES_HOME) {
        $env:HERMES_HOME = $root
        $changed = $true
    } elseif ($env:HERMES_HOME.TrimEnd('\') -ne $root) {
        $env:HERMES_HOME = $root
        $changed = $true
    }

    if ($changed -and -not $Quiet) {
        Write-HermesOk ('HERMES_HOME = ' + $root)
    }
    return $root
}

function Test-HermesAuthJsonHealth {
    param([string]$Root = '')
    if (-not $Root) { $Root = Get-HermesRuntimeRoot }
    $authPath = Join-Path $Root 'auth.json'
    if (-not (Test-Path -LiteralPath $authPath)) {
        return @{ Ok = $true; Message = 'auth.json ontbreekt (OK voor fresh install)' }
    }
    try {
        $parsed = Get-Content -LiteralPath $authPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $ok = ($null -ne $parsed) -and (
            ($parsed.PSObject.Properties.Name -contains 'providers') -or
            ($parsed.PSObject.Properties.Name -contains 'credential_pool')
        )
        if (-not $ok) {
            return @{ Ok = $false; Message = 'auth.json ongeldig — run verify_hermes_home of FIX_GEMINI_CREDENTIAL_POOL.bat' }
        }
        return @{ Ok = $true; Message = 'auth.json parsebaar' }
    } catch {
        return @{ Ok = $false; Message = ('auth.json parse error: ' + $_.Exception.Message) }
    }
}

function Get-HermesGatewayCmdPaths {
    $root = Get-HermesRuntimeRoot
    $svcDir = Join-Path $root 'gateway-service'
    if (-not (Test-Path -LiteralPath $svcDir)) { return @() }
    return @(Get-ChildItem -LiteralPath $svcDir -Filter '*.cmd' -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
}

function Test-HermesGatewayHomeAlignment {
    param([switch]$Quiet)
    $expected = (Get-HermesRuntimeRoot).TrimEnd('\')
    $misaligned = @()
    foreach ($cmdPath in (Get-HermesGatewayCmdPaths)) {
        $content = Get-Content -LiteralPath $cmdPath -Raw -Encoding UTF8
        if ($content -match 'set\s+"HERMES_HOME=([^"]+)"') {
            $found = $Matches[1].TrimEnd('\')
            if ($found -ne $expected) {
                $misaligned += @{ Path = $cmdPath; Found = $found; Expected = $expected }
            }
        }
    }
    if ($misaligned.Count -eq 0) {
        if (-not $Quiet) { Write-HermesOk 'Gateway gateway.cmd HERMES_HOME aligned' }
        return $true
    }
    foreach ($item in $misaligned) {
        if (-not $Quiet) {
            Write-HermesWarn ('Gateway HERMES_HOME mismatch in ' + $item.Path)
            Write-Host ('       found: ' + $item.Found + ' expected: ' + $item.Expected) -ForegroundColor Yellow
            Write-Host '       Fix: hermes gateway restart (of hermes gateway install)' -ForegroundColor Yellow
        }
    }
    return $false
}

$script:HermesHybridTextAuxTasks = @(
    'compression', 'web_extract', 'mcp', 'approval',
    'title_generation', 'skills_hub', 'triage_specifier', 'curator'
)

function Test-HermesAuxiliaryPresetDrift {
    param([switch]$Quiet)
    $runtimeCfg = Get-HermesCanonicalConfigPath
    if (-not (Test-Path -LiteralPath $runtimeCfg)) { return $false }
    try {
        $raw = Get-Content -LiteralPath $runtimeCfg -Raw -Encoding UTF8
        if ($raw -notmatch '(?ms)^auxiliary:\s*(.+?)(?=^\S|\z)') { return $false }
        $block = $Matches[1]
    } catch {
        return $false
    }
    $autoTasks = [System.Collections.Generic.List[string]]::new()
    foreach ($task in $script:HermesHybridTextAuxTasks) {
        if ($block -match "(?ms)^\s*$task\s*:\s*(.+?)(?=^\s+\w|\z)") {
            $taskBlock = $Matches[1]
            if ($taskBlock -match '(?m)^\s*provider\s*:\s*auto\s*$') {
                [void]$autoTasks.Add($task)
            }
        }
    }
    if ($autoTasks.Count -eq 0) { return $false }
    $msg = 'Auxiliary preset drift: tekst-taken nog op provider auto: ' + ($autoTasks -join ', ')
    if (-not $Quiet) {
        Write-HermesWarn $msg
        Write-Host '       Fix: windows\APPLY_AUXILIARY_HYBRID_PRESET.bat' -ForegroundColor Yellow
    }
    return $true
}
