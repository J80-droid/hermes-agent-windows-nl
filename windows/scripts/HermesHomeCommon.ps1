# Gedeelde Hermes Windows home-paden (runtime vs legacy split-home).
# Dot-source: . (Join-Path $PSScriptRoot 'HermesHomeCommon.ps1')

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
        if (-not $Quiet) {
            Write-Host '[OK] Geen config drift (split-home)' -ForegroundColor Green
        }
        Test-HermesAuxiliaryPresetDrift -Quiet:$Quiet | Out-Null
        return $true
    }

    foreach ($issue in $issues) {
        if (-not $Quiet) {
            Write-Host ('[FAIL] ' + $issue) -ForegroundColor Red
        }
    }
    return $false
}

function Ensure-UserHermesHomeRoot {
    param(
        [switch]$FixUserEnv,
        [switch]$Quiet
    )
    $root = (Get-HermesRuntimeRoot).TrimEnd('\')
    $changed = $false

    $userHome = [Environment]::GetEnvironmentVariable('HERMES_HOME', 'User')
    if ($userHome -and (Test-HermesProfileSubdirPath $userHome)) {
        if (-not $Quiet) {
            Write-Host ('[WARN] User HERMES_HOME wijst naar profielmap: ' + $userHome) -ForegroundColor Yellow
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
            Write-Host ('[INFO] User HERMES_HOME niet gezet — runtime root: ' + $root) -ForegroundColor Cyan
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
        Write-Host ('[OK] HERMES_HOME = ' + $root) -ForegroundColor Green
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
        if (-not $Quiet) { Write-Host '[OK] Gateway gateway.cmd HERMES_HOME aligned' -ForegroundColor Green }
        return $true
    }
    foreach ($item in $misaligned) {
        if (-not $Quiet) {
            Write-Host ('[WARN] Gateway HERMES_HOME mismatch in ' + $item.Path) -ForegroundColor Yellow
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
        Write-Host ('[WARN] ' + $msg) -ForegroundColor Yellow
        Write-Host '       Fix: windows\APPLY_AUXILIARY_HYBRID_PRESET.bat' -ForegroundColor Yellow
    }
    return $true
}
