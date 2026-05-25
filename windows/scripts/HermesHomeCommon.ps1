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

function Test-HermesConfigDrift {
    param(
        [switch]$Strict,
        [switch]$Quiet
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
            $issues.Add(
                'Model/provider incoherentie (auth.json vs config) — run windows\REPAIR_MODEL_PROVIDER.bat of hermes doctor --fix'
            )
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
os.environ['HERMES_HOME'] = r'$runtimeRoot'
os.environ.setdefault('HERMES_WIN_PREFER_LOCALAPPDATA', '1')
from hermes_cli.config import load_config
from hermes_cli.model_runtime_config import detect_model_provider_incoherence
issues = detect_model_provider_incoherence(load_config())
if not issues:
    sys.exit(0)
for i in issues:
    print(f'{i.severity}: {i.message}')
sys.exit(1)
"@
        & $python -c $code 2>&1 | ForEach-Object {
            if (-not $Quiet) { Write-HermesFail $_ }
        }
        return $false
    } catch {
        if (-not $Quiet) {
            Write-HermesFail "Model/provider coherence check mislukt: $($_.Exception.Message)"
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
